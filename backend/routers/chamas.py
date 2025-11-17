# backend/routers/chamas.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.crud import create_chama, get_user_chamas, get_chama
from backend.schemas import Chama, ChamaCreate, ChamaWithMembers, Membership, ChamaSummary, ChamaAnalytics
from backend.security import get_current_user, require_chama_role
from backend.models.membership import MembershipRole
from backend.models.user import User
from backend.models.membership import Membership as MembershipModel
from backend.exceptions import ResourceNotFoundError, AuthorizationError

router = APIRouter(
    tags=["Chamas"],
)

# --- Create a new Chama ---
@router.post("/", response_model=ChamaWithMembers, status_code=status.HTTP_201_CREATED)
def create_new_chama(
    chama: ChamaCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new Chama with the current user as owner.
    """
    new_chama = create_chama(db=db, chama=chama, owner_id=current_user.id)

    # Trigger background notification task
    from backend.tasks.notifications import notify_chama_created
    notify_chama_created.delay(chama_id=new_chama.id, owner_id=current_user.id)

    # Build memberships for response - include chama_id
    return ChamaWithMembers(
        id=new_chama.id,
        name=new_chama.name,
        description=new_chama.description,
        created_at=new_chama.created_at,
        created_by_user_id=new_chama.created_by_user_id,
        memberships=[Membership(user_id=current_user.id, chama_id=new_chama.id, role="owner")]
    )

# --- Get all Chamas for current user ---
@router.get("/", response_model=List[ChamaWithMembers])
def list_user_chamas(
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    List all Chamas where the current user is a member.
    """
    chamas = get_user_chamas(db, user_id=current_user.id)
    # Attach memberships to each Chama
    chamas_with_members = []
    for chama in chamas:
        memberships = [
            Membership(user_id=m.user_id, chama_id=m.chama_id, role=m.role)
            for m in db.query(MembershipModel).filter(MembershipModel.chama_id == chama.id).all()
        ]
        chamas_with_members.append(
            ChamaWithMembers(
                id=chama.id,
                name=chama.name,
                description=chama.description,
                created_at=chama.created_at,
                created_by_user_id=chama.created_by_user_id,
                memberships=memberships
            )
        )
    return chamas_with_members

# --- Get specific Chama details ---
@router.get("/{chama_id}", response_model=ChamaWithMembers)
def get_chama_details(
    chama_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific Chama. User must be a member.
    """
    chama = get_chama(db, chama_id=chama_id)
    if not chama:
        raise ResourceNotFoundError("Chama", str(chama_id))

    # Check if user is a member of this chama
    membership = db.query(MembershipModel).filter(
        Membership.chama_id == chama_id,
        MembershipModel.user_id == current_user.id
    ).first()

    if not membership:
        raise AuthorizationError("Not a member of this chama")

    # Populate memberships for response
    memberships = [
        Membership(user_id=m.user_id, chama_id=m.chama_id, role=m.role)
        for m in db.query(MembershipModel).filter(MembershipModel.chama_id == chama.id).all()
    ]
    return ChamaWithMembers(
        id=chama.id,
        name=chama.name,
        description=chama.description,
        created_at=chama.created_at,
        created_by_user_id=chama.created_by_user_id,
        memberships=memberships
    )

# --- Get Chama summary (cached, fast) ---
@router.get("/{chama_id}/summary", response_model=dict)
def get_chama_summary(
    chama_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get cached summary of Chama metrics. Fast endpoint for dashboards and mobile apps.
    """
    # Only members can view summary
    membership = require_chama_role(chama_id, [
        MembershipRole.owner, MembershipRole.treasurer, MembershipRole.member
    ])(current_user, db=None)

    # Import Redis for caching
    import redis
    from backend.config import settings

    # Try to get cached summary
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
                       socket_connect_timeout=1, socket_timeout=1)
        cached_data = r.get(f"chama:{chama_id}:summary")

        if cached_data:
            import json
            return json.loads(cached_data)
    except Exception as e:
        # Log error but don't fail - we'll recompute
        from backend.logging_config import setup_logging
        logger = setup_logging()
        logger.warning(f"Redis connection error for summary cache: {str(e)}")

    # If no cached data, trigger background computation and return placeholder
    from backend.tasks.analytics import recompute_chama_summaries
    recompute_chama_summaries.delay(chama_id)

    # Return a placeholder saying data is being computed
    from datetime import datetime, timezone
    return {
        "chama_id": chama_id,
        "name": "Loading...",
        "total_members": 0,
        "total_contributions": 0.0,
        "total_contributions_count": 0,
        "latest_contribution": None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "computing"
    }

# --- Get Chama analytics (cached, fast) ---
@router.get("/{chama_id}/analytics", response_model=dict)
def get_chama_analytics(
    chama_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get cached analytics data for Chama. Structured for dashboards and charts.
    """
    # Only members can view analytics
    membership = require_chama_role(chama_id, [
        MembershipRole.owner, MembershipRole.treasurer, MembershipRole.member
    ])(current_user, db=None)

    # Import Redis for caching
    import redis
    from backend.config import settings

    # Try to get cached analytics
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
                       socket_connect_timeout=1, socket_timeout=1)
        cached_data = r.get(f"chama:{chama_id}:analytics")

        if cached_data:
            import json
            return json.loads(cached_data)
    except Exception as e:
        # Log error but don't fail - we'll recompute
        from backend.logging_config import setup_logging
        logger = setup_logging()
        logger.warning(f"Redis connection error for analytics cache: {str(e)}")

    # If no cached data, trigger background computation and return placeholder
    from backend.tasks.analytics import precompute_chama_analytics
    precompute_chama_analytics.delay(chama_id)

    # Return a placeholder saying data is being computed
    from datetime import datetime, timezone
    return {
        "chama_id": chama_id,
        "monthly_contributions": [],
        "top_contributors": [],
        "average_contribution": 0.0,
        "contribution_frequency": {"weekly": 0, "monthly": 0},
        "growth_rate": "0%",
        "trend": "stable",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "status": "computing"
    }
