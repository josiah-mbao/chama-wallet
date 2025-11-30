"""
Integration tests for Celery background tasks.
Tests analytics, notifications, and other background processing tasks.
"""
import pytest
from unittest.mock import Mock, patch

from backend.tasks.analytics import (
    recompute_chama_summaries,
    precompute_chama_analytics,
    generate_monthly_reports,
    bulk_data_operations
)
from backend.tasks.notifications import (
    notify_contribution_created,
    notify_member_added,
    notify_chama_created
)


class TestAnalyticsTasks:
    """Test analytics background tasks."""

    def test_bulk_data_operations_recalculate_summaries(self):
        """Test bulk operation to recalculate summaries."""
        with patch('backend.tasks.analytics.recompute_chama_summaries') as mock_task:
            mock_task.delay = Mock()
            bulk_data_operations("recalculate_all_summaries", 123)
            mock_task.delay.assert_called_once_with(123)

    def test_bulk_data_operations_unknown_type(self):
        """Test bulk operation with unknown operation type."""
        bulk_data_operations("unknown_operation", 123)
        assert True

    @patch('backend.tasks.analytics.logger')
    def test_recompute_chama_summaries_handles_errors(self, mock_logger):
        """Test that summary recomputation handles errors gracefully."""
        recompute_chama_summaries(999)
        assert mock_logger.error.called

    @patch('backend.tasks.analytics.logger')
    def test_precompute_chama_analytics_handles_errors(self, mock_logger):
        """Test that analytics precomputation handles errors gracefully."""
        precompute_chama_analytics(999)
        assert mock_logger.error.called

    @patch('backend.tasks.analytics.logger')
    def test_generate_monthly_reports_handles_errors(self, mock_logger):
        """Test that monthly reports handle errors gracefully."""
        generate_monthly_reports(999)
        assert mock_logger.error.called


class TestNotificationTasks:
    """Test notification background tasks."""

    def test_notify_contribution_created_handles_errors(self):
        """Test contribution notification handles errors gracefully."""
        # Should not crash even with invalid chama_id
        notify_contribution_created(999, 456, 100.0, 789)

    def test_notify_member_added_handles_errors(self):
        """Test member addition notification handles errors gracefully."""
        # Should not crash even with invalid chama_id
        notify_member_added(999, 456, 789)

    def test_notify_chama_created_handles_errors(self):
        """Test chama creation notification handles errors gracefully."""
        # Should not crash even with invalid chama_id
        notify_chama_created(999, 456)


class TestCeleryTaskImports:
    """Test that Celery tasks can be imported and are callable."""

    def test_analytics_tasks_importable(self):
        """Test that analytics tasks are importable."""
        assert callable(recompute_chama_summaries)
        assert callable(precompute_chama_analytics)
        assert callable(generate_monthly_reports)
        assert callable(bulk_data_operations)

    def test_notification_tasks_importable(self):
        """Test that notification tasks are importable."""
        assert callable(notify_contribution_created)
        assert callable(notify_member_added)
        assert callable(notify_chama_created)

    def test_tasks_have_celery_app_attribute(self):
        """Test that tasks have Celery app binding."""
        from backend.celery_app import celery_app

        # Check that tasks are registered with Celery
        assert hasattr(recompute_chama_summaries, 'delay')
        assert hasattr(notify_contribution_created, 'delay')
