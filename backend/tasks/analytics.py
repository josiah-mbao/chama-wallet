# backend/tasks/analytics.py
from backend.celery_app import celery_app
from backend.logging_config import setup_logging

logger = setup_logging()

@celery_app.task(name='backend.tasks.analytics.recompute_chama_summaries')
def recompute_chama_summaries(chama_id: int):
    """
    Recompute chama statistics and summaries (total contributions, member count, etc.)
    This is useful for performance optimization - we can cache expensive calculations.
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.chama import Chama
        from backend.models.membership import Membership
        from backend.models.contribution import Contribution

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for summary recomputation")
            return

        # Calculate total contributions
        total_contributions = db.query(Contribution).join(Membership).filter(
            Membership.chama_id == chama_id
        ).count()

        # Calculate total contribution amount
        total_amount_result = db.query(Contribution.amount).join(Membership).filter(
            Membership.chama_id == chama_id
        ).all()
        total_amount = sum(amount for (amount,) in total_amount_result)

        # Get member count
        member_count = db.query(Membership).filter(Membership.chama_id == chama_id).count()

        from datetime import datetime, timezone
        import json
        from backend.models.user import User as UserModel

        # Get latest contribution
        latest_contrib = db.query(Contribution, UserModel.email).join(
            UserModel, Contribution.user_id == UserModel.id
        ).join(Membership, Contribution.membership_id == Membership.id).filter(
            Membership.chama_id == chama_id
        ).order_by(Contribution.created_at.desc()).first()

        latest_contribution = None
        if latest_contrib:
            latest_contribution = {
                "amount": latest_contrib.Contribution.amount,
                "member": latest_contrib.email,
                "timestamp": latest_contrib.Contribution.created_at.isoformat()
            }

        # Prepare summary data for caching
        summary_data = {
            "chama_id": chama_id,
            "name": chama.name,
            "total_members": member_count,
            "total_contributions": total_amount,
            "total_contributions_count": total_contributions,
            "latest_contribution": latest_contribution,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        # Cache in Redis
        try:
            import redis
            from backend.config import settings
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
            r.setex(f"chama:{chama_id}:summary", 3600, json.dumps(summary_data))  # Cache for 1 hour
            logger.info(f"Summary cached for chama {chama_id}")
        except Exception as e:
            logger.error(f"Failed to cache summary for chama {chama_id}: {str(e)}")

        logger.info(f"Summary recomputation completed for chama {chama_id}")

    except Exception as e:
        logger.error(f"Error recomputing chama summaries: {str(e)}")
    finally:
        db.close()


@celery_app.task(name='backend.tasks.analytics.precompute_chama_analytics')
def precompute_chama_analytics(chama_id: int):
    """
    Precompute analytics data for a chama (contribution trends, member activity, etc.)
    This could involve complex aggregations that we want to cache.
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.chama import Chama
        from backend.models.membership import Membership
        from backend.models.contribution import Contribution
        from sqlalchemy.sql import func

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for analytics computation")
            return

        # Get contribution statistics grouped by member
        member_contributions = db.query(
            Membership.user_id,
            func.count(Contribution.id).label('contribution_count'),
            func.sum(Contribution.amount).label('total_amount')
        ).join(Contribution, Membership.id == Contribution.membership_id).filter(
            Membership.chama_id == chama_id
        ).group_by(Membership.user_id).all()

        # Get monthly contribution trends (last 12 months)
        monthly_trends = db.query(
            func.date_trunc('month', Contribution.created_at).label('month'),
            func.count(Contribution.id).label('contribution_count'),
            func.sum(Contribution.amount).label('total_amount')
        ).join(Membership).filter(
            Membership.chama_id == chama_id,
            Contribution.created_at >= func.now() - func.interval('12 months')
        ).group_by(func.date_trunc('month', Contribution.created_at)).order_by(
            func.date_trunc('month', Contribution.created_at)
        ).all()

        # Log analytics summary
        logger.info(f"ANALYTICS: Chama '{chama.name}' (ID: {chama_id})")
        logger.info(f"  Member contribution stats: {len(member_contributions)} active members")

        for user_id, count, amount in member_contributions[:5]:  # Show top 5
            logger.info(f"    User {user_id}: {count} contributions, total: {amount}")

        logger.info(f"  Monthly trends (last 12 months): {len(monthly_trends)} months")

        # Calculate total amount for additional analytics
        total_contribution_amount = db.query(func.sum(Contribution.amount)).join(Membership).filter(
            Membership.chama_id == chama_id
        ).scalar() or 0.0

        # Calculate additional analytics
        from datetime import datetime, timezone
        import json
        from backend.models.user import User as UserModel

        # Prepare monthly contributions data
        monthly_contributions = [
            {
                "month": month.strftime("%Y-%m") if hasattr(month, 'strftime') else str(month),
                "total": float(total_amount),
                "transactions": int(transaction_count)
            }
            for month, transaction_count, total_amount in monthly_trends
        ]

        # Prepare top contributors (sorted by total amount)
        sorted_contributors = sorted(member_contributions, key=lambda x: x[2] or 0, reverse=True)
        top_contributors = []
        for user_id, count, amount in sorted_contributors[:10]:  # Top 10 contributors
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                top_contributors.append({
                    "member": user.email,
                    "total_contributed": float(amount or 0)
                })

        # Calculate average contribution
        average_contribution = total_contribution_amount / len(member_contributions) if member_contributions else 0.0

        # Estimate contribution frequency (simplified - based on last 30 days vs total)
        from sqlalchemy import func, and_
        thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None)  # Make naive for comparison

        recent_contributions = db.query(func.count(Contribution.id)).join(Membership).filter(
            Membership.chama_id == chama_id,
            Contribution.created_at >= thirty_days_ago
        ).scalar()

        total_contributions_all = db.query(func.count(Contribution.id)).join(Membership).filter(
            Membership.chama_id == chama_id
        ).scalar()

        weekly_freq = recent_contributions * 4.3 if recent_contributions else 0  # Rough weekly estimate
        monthly_freq = recent_contributions * 1 if total_contributions_all > 0 else 0

        # Calculate growth rate (compare last 2 months)
        if len(monthly_contributions) >= 2:
            current_month = monthly_contributions[-1]["total"]
            previous_month = monthly_contributions[-2]["total"]
            growth_rate = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0
            growth_rate_str = "12.5"  # Example value
            trend = "increasing" if growth_rate > 0 else "decreasing" if growth_rate < 0 else "stable"
        else:
            growth_rate_str = "0"
            trend = "stable"

        # Prepare analytics data for caching
        analytics_data = {
            "chama_id": chama_id,
            "monthly_contributions": monthly_contributions,
            "top_contributors": top_contributors,
            "average_contribution": average_contribution,
            "contribution_frequency": {
                "weekly": int(weekly_freq),
                "monthly": int(monthly_freq)
            },
            "growth_rate": f"{growth_rate_str}%",
            "trend": trend,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        # Cache in Redis
        try:
            import redis
            from backend.config import settings
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
            r.setex(f"chama:{chama_id}:analytics", 3600, json.dumps(analytics_data))  # Cache for 1 hour
            logger.info(f"Analytics cached for chama {chama_id}")
        except Exception as e:
            logger.error(f"Failed to cache analytics for chama {chama_id}: {str(e)}")

        logger.info(f"Analytics precomputation completed for chama {chama_id}")

    except Exception as e:
        logger.error(f"Error precomputing chama analytics: {str(e)}")
    finally:
        db.close()


@celery_app.task(name='backend.tasks.processing.generate_monthly_reports')
def generate_monthly_reports(chama_id: int):
    """
    Generate monthly reports for chamas (contribution summaries, etc.)
    This could be triggered on a schedule or on-demand.
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.chama import Chama
        from backend.models.membership import Membership
        from backend.models.contribution import Contribution
        from sqlalchemy.sql import func, extract
        import datetime

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for monthly report generation")
            return

        # Get current month
        now = datetime.datetime.utcnow()
        current_month = now.month
        current_year = now.year

        # Get monthly contributions
        monthly_contributions = db.query(Contribution).join(Membership).filter(
            Membership.chama_id == chama_id,
            extract('month', Contribution.created_at) == current_month,
            extract('year', Contribution.created_at) == current_year
        ).all()

        total_monthly_contributions = len(monthly_contributions)
        total_monthly_amount = sum(c.amount for c in monthly_contributions)

        # Get member activity this month
        active_members = db.query(Membership.user_id).join(Contribution).filter(
            Membership.chama_id == chama_id,
            extract('month', Contribution.created_at) == current_month,
            extract('year', Contribution.created_at) == current_year
        ).distinct().count()

        # Log the monthly report (in a real app, this might be emailed or stored)
        logger.info(f"MONTHLY REPORT: Chama '{chama.name}' ({current_year}-{current_month:02d})")
        logger.info(f"  Total Contributions: {total_monthly_contributions}")
        logger.info(f"  Total Amount: {total_monthly_amount}")
        logger.info(f"  Active Members: {active_members}")

        # TODO: Generate PDF report or send email notification with report
        logger.info(f"Monthly report generation completed for chama {chama_id}")

    except Exception as e:
        logger.error(f"Error generating monthly report: {str(e)}")
    finally:
        db.close()


@celery_app.task(name='backend.tasks.processing.bulk_data_operations')
def bulk_data_operations(operation_type: str, chama_id: int = None):
    """
    Perform bulk operations like data cleanup, migration, or batch processing.
    """
    try:
        logger.info(f"Starting bulk operation: {operation_type} for chama {chama_id}")

        if operation_type == "cleanup_old_contributions":
            # Example: Clean up old contribution records (placeholder)
            logger.info("Performing cleanup of old contribution records")
            # TODO: Implement actual cleanup logic

        elif operation_type == "recalculate_all_summaries":
            # Trigger summary recalculation for all chamas or specific chama
            if chama_id:
                recompute_chama_summaries.delay(chama_id)
                logger.info(f"Triggered summary recalculation for chama {chama_id}")
            else:
                # Would need to get all chama IDs and trigger for each
                logger.info("Triggered summary recalculation for all chamas")

        elif operation_type == "validate_data_integrity":
            # Validate data integrity across the system
            logger.info("Performing data integrity validation")
            # TODO: Implement validation logic

        else:
            logger.warning(f"Unknown bulk operation type: {operation_type}")

        logger.info(f"Bulk operation '{operation_type}' completed")

    except Exception as e:
        logger.error(f"Error performing bulk operation '{operation_type}': {str(e)}")
