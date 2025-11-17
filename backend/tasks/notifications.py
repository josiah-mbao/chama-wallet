# backend/tasks/notifications.py
from backend.celery_app import celery_app
from backend.logging_config import setup_logging

logger = setup_logging()

@celery_app.task(name='backend.tasks.notifications.notify_contribution_created')
def notify_contribution_created(chama_id: int, user_id: int, amount: float, contribution_id: int):
    """
    Send notification to chama owners/treasurers when a contribution is created.
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.membership import Membership, MembershipRole
        from backend.models.chama import Chama
        from backend.models.user import User as UserModel

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for notification")
            return

        # Get the contributor
        contributor = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not contributor:
            logger.error(f"User {user_id} not found for notification")
            return

        # Get owners and treasurers to notify
        recipients = db.query(UserModel).join(Membership).filter(
            Membership.chama_id == chama_id,
            Membership.role.in_([MembershipRole.owner, MembershipRole.treasurer])
        ).all()

        # TODO: Implement actual notification mechanism (email, push, etc.)
        # For now, just log the notification
        for recipient in recipients:
            logger.info(
                f"NOTIFICATION: To {recipient.email} - "
                f"New contribution of {amount} by {contributor.email} in chama '{chama.name}'"
            )

        logger.info(f"Contribution notification sent for chama {chama_id}, contribution {contribution_id}")

    except Exception as e:
        logger.error(f"Error sending contribution notification: {str(e)}")
    finally:
        db.close()


@celery_app.task(name='backend.tasks.notifications.notify_member_added')
def notify_member_added(chama_id: int, new_member_id: int, added_by_id: int):
    """
    Send notification when a member is added to a chama.
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.user import User as UserModel
        from backend.models.chama import Chama

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for member addition notification")
            return

        # Get the new member
        new_member = db.query(UserModel).filter(UserModel.id == new_member_id).first()
        if not new_member:
            logger.error(f"New member {new_member_id} not found for notification")
            return

        # Get the person who added them
        adder = db.query(UserModel).filter(UserModel.id == added_by_id).first()
        if not adder:
            logger.error(f"Adder {added_by_id} not found for notification")
            return

        # Notify the new member
        logger.info(
            f"NOTIFICATION: To {new_member.email} - "
            f"You have been added to chama '{chama.name}' by {adder.email}"
        )

        # Optionally notify other members about the new addition
        # For now, just log it
        logger.info(
            f"Member addition notification sent for chama {chama_id}, "
            f"new member {new_member.email} added by {adder.email}"
        )

    except Exception as e:
        logger.error(f"Error sending member addition notification: {str(e)}")
    finally:
        db.close()


@celery_app.task(name='backend.tasks.notifications.notify_chama_created')
def notify_chama_created(chama_id: int, owner_id: int):
    """
    Send notification when a chama is created (primarily to the owner).
    """
    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.user import User as UserModel
        from backend.models.chama import Chama

        db = next(get_db())

        # Get chama details
        chama = db.query(Chama).filter(Chama.id == chama_id).first()
        if not chama:
            logger.error(f"Chama {chama_id} not found for creation notification")
            return

        # Get the owner
        owner = db.query(UserModel).filter(UserModel.id == owner_id).first()
        if not owner:
            logger.error(f"Owner {owner_id} not found for notification")
            return

        # Welcome notification to owner
        logger.info(
            f"NOTIFICATION: To {owner.email} - "
            f"Your chama '{chama.name}' has been created successfully!"
        )

        logger.info(f"Chama creation notification sent for chama {chama_id}")

    except Exception as e:
        logger.error(f"Error sending chama creation notification: {str(e)}")
    finally:
        db.close()
