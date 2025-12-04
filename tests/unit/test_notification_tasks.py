"""
Unit tests for notification background tasks.
Tests contribution notifications, member additions, and chama creation alerts.
"""
from unittest.mock import Mock, patch, MagicMock

from backend.tasks.notifications import (
    notify_contribution_created,
    notify_member_added,
    notify_chama_created
)


class TestNotifyContributionCreated:
    """Test contribution creation notifications."""

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_contribution_created_success(self, mock_logger, mock_get_db):
        """Test successful contribution notification to owners/treasurers."""
        # Setup database mock
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Test Chama"

        # Setup contributor
        mock_contributor = Mock()
        mock_contributor.email = "contributor@example.com"

        # Setup recipients (owners/treasurers)
        mock_recipient1 = Mock()
        mock_recipient1.email = "owner1@example.com"
        mock_recipient2 = Mock()
        mock_recipient2.email = "treasurer1@example.com"

        # Use side_effect to handle the sequence of queries
        mock_db.query.side_effect = [
            # First query: Chama lookup
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_chama)))),
            # Second query: Contributor lookup
            MagicMock(filter=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_contributor)))),
            # Third query: Recipients lookup
            MagicMock(
                join=MagicMock(return_value=MagicMock(
                    filter=MagicMock(return_value=MagicMock(
                        all=MagicMock(return_value=[mock_recipient1, mock_recipient2])
                    ))
                ))
            )
        ]

        # Execute
        notify_contribution_created(1, 123, 500.0, 456)

        # Verify logging - check that at least one completion message was logged
        log_calls = mock_logger.info.call_args_list
        assert len(log_calls) >= 1

        # Check for completion message
        messages = [call[0][0] for call in log_calls]
        assert any("Contribution notification sent for chama 1" in msg for msg in messages)

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    @patch('backend.models.chama.Chama')
    @patch('backend.models.user.User')
    @patch('backend.models.membership.Membership')
    @patch('backend.models.membership.MembershipRole')
    def test_notify_contribution_created_chama_not_found(self,
                                                         mock_membership_role,
                                                         mock_membership,
                                                         mock_user,
                                                         mock_chama,
                                                         mock_logger,
                                                         mock_get_db):
        """Test contribution notification when chama doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Mock the query to return None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        notify_contribution_created(999, 123, 500.0, 456)

        # Debug: print all error calls
        for call in mock_logger.error.call_args_list:
            print(f"ERROR LOGGED: {call}")

        # Debug: print all info calls
        for call in mock_logger.info.call_args_list:
            print(f"INFO LOGGED: {call}")

        mock_logger.error.assert_called_with("Chama 999 not found for notification")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_contribution_created_contributor_not_found(self, mock_logger, mock_get_db):
        """Test contribution notification when contributor doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama exists but contributor doesn't
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Test Chama"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, None]

        notify_contribution_created(1, 999, 500.0, 456)

        mock_logger.error.assert_called_with("User 999 not found for notification")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_contribution_created_no_recipients(self, mock_logger, mock_get_db):
        """Test contribution notification when no owners/treasurers exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama and users exist
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Test Chama"
        mock_contributor = Mock()
        mock_contributor.email = "contributor@example.com"

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, mock_contributor]
        # No recipients found
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        notify_contribution_created(1, 123, 500.0, 456)

        # Should still complete without errors
        mock_logger.info.assert_called()


class TestNotifyMemberAdded:
    """Test member addition notifications."""

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_member_added_success(self, mock_logger, mock_get_db):
        """Test successful member addition notification."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Test Chama"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama]

        # Setup new member
        mock_new_member = Mock()
        mock_new_member.email = "newmember@example.com"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, mock_new_member]

        # Setup adder
        mock_adder = Mock()
        mock_adder.email = "adder@example.com"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, mock_new_member, mock_adder]

        # Execute
        notify_member_added(1, 123, 456)

        # Verify notification logging
        log_calls = mock_logger.info.call_args_list
        messages = [call[0][0] for call in log_calls]

        # Check new member notification
        assert any("NOTIFICATION: To newmember@example.com" in msg for msg in messages)
        assert any("You have been added to chama 'Test Chama'" in msg for msg in messages)
        assert any("by adder@example.com" in msg for msg in messages)

        # Check addition logging
        assert any("Member addition notification sent for chama 1" in msg for msg in messages)

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_member_added_chama_not_found(self, mock_logger, mock_get_db):
        """Test member addition notification when chama doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]
        mock_db.query.return_value.filter.return_value.first.return_value = None

        notify_member_added(999, 123, 456)

        mock_logger.error.assert_called_with("Chama 999 not found for member addition notification")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_member_added_member_not_found(self, mock_logger, mock_get_db):
        """Test member addition notification when new member doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama exists but member doesn't
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Test Chama"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, None]

        notify_member_added(1, 999, 456)

        mock_logger.error.assert_called_with("New member 999 not found for notification")


class TestNotifyChamaCreated:
    """Test chama creation notifications."""

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_chama_created_success(self, mock_logger, mock_get_db):
        """Test successful chama creation notification."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "New Chama"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chama

        # Setup owner
        mock_owner = Mock()
        mock_owner.email = "owner@example.com"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, mock_owner]

        # Execute
        notify_chama_created(1, 123)

        # Verify welcome notification
        mock_logger.info.assert_called_with(
            "NOTIFICATION: To owner@example.com - Your chama 'New Chama' has been created successfully!"
        )

        # Verify completion logging
        log_calls = mock_logger.info.call_args_list
        messages = [call[0][0] for call in log_calls]
        assert any("Chama creation notification sent for chama 1" in msg for msg in messages)

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_chama_created_chama_not_found(self, mock_logger, mock_get_db):
        """Test chama creation notification when chama doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]
        mock_db.query.return_value.filter.return_value.first.return_value = None

        notify_chama_created(999, 123)

        mock_logger.error.assert_called_with("Chama 999 not found for creation notification")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_chama_created_owner_not_found(self, mock_logger, mock_get_db):
        """Test chama creation notification when owner doesn't exist."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup chama exists but owner doesn't
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "New Chama"
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_chama, None]

        notify_chama_created(1, 999)

        mock_logger.error.assert_called_with("Owner 999 not found for notification")


class TestNotificationTaskErrorHandling:
    """Test error handling across notification tasks."""

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_contribution_created_database_error(self, mock_logger, mock_get_db):
        """Test contribution notification handles database errors."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]
        mock_db.query.side_effect = Exception("Database connection failed")

        notify_contribution_created(1, 123, 500.0, 456)

        mock_logger.error.assert_called_with("Error sending contribution notification: Database connection failed")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_member_added_database_error(self, mock_logger, mock_get_db):
        """Test member addition notification handles database errors."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]
        mock_db.query.side_effect = Exception("Database connection failed")

        notify_member_added(1, 123, 456)

        mock_logger.error.assert_called_with("Error sending member addition notification: Database connection failed")

    @patch('backend.database.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_notify_chama_created_database_error(self, mock_logger, mock_get_db):
        """Test chama creation notification handles database errors."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]
        mock_db.query.side_effect = Exception("Database connection failed")

        notify_chama_created(1, 123)

        mock_logger.error.assert_called_with("Error sending chama creation notification: Database connection failed")


class TestNotificationTaskIntegration:
    """Integration tests for notification tasks."""

    @patch('backend.tasks.notifications.get_db')
    @patch('backend.tasks.notifications.logger')
    def test_contribution_notification_complete_flow(self, mock_logger, mock_get_db):
        """Test complete contribution notification flow."""
        mock_db = MagicMock()
        mock_get_db.return_value.__iter__.return_value = [mock_db]

        # Setup complete scenario
        mock_chama = Mock()
        mock_chama.id = 1
        mock_chama.name = "Integration Test Chama"

        mock_contributor = Mock()
        mock_contributor.email = "contributor@test.com"

        mock_owner = Mock()
        mock_owner.email = "owner@test.com"
        mock_treasurer = Mock()
        mock_treasurer.email = "treasurer@test.com"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_chama, mock_contributor
        ]
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            mock_owner, mock_treasurer
        ]

        # Execute
        notify_contribution_created(1, 123, 750.50, 456)

        # Verify complete notification flow
        log_calls = mock_logger.info.call_args_list
        messages = [call[0][0] for call in log_calls]

        # Check all expected notifications
        assert any("NOTIFICATION: To owner@test.com" in msg and "750.5" in msg for msg in messages)
        assert any("NOTIFICATION: To treasurer@test.com" in msg and "750.5" in msg for msg in messages)
        assert any("by contributor@test.com" in msg for msg in messages)
        assert any("in chama 'Integration Test Chama'" in msg for msg in messages)
        assert any("Contribution notification sent for chama 1" in msg for msg in messages)
