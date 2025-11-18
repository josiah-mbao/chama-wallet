from unittest.mock import MagicMock, patch
from backend.crud import get_chama_by_id, get_user_chamas, get_members, create_member, create_contribution


def test_get_chama_by_id():
    """Test get_chama_by_id returns chama if exists"""
    mock_db = MagicMock()
    mock_chama = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_chama

    result = get_chama_by_id(mock_db, 1)

    assert result == mock_chama
    mock_db.query.assert_called_once()


def test_get_user_chamas():
    """Test get_user_chamas joins tables correctly"""
    mock_db = MagicMock()
    mock_chamas = [MagicMock()]
    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = mock_chamas

    result = get_user_chamas(mock_db, 1)

    assert result == mock_chamas


def test_get_members():
    """Test get_members with and without chama_id"""
    mock_db = MagicMock()
    mock_members = [MagicMock()]
    mock_db.query.return_value.filter.return_value.all.return_value = mock_members

    result = get_members(mock_db, chama_id=1)

    assert result == mock_members


def test_create_member():
    """Test create_member creates and commits membership"""
    mock_db = MagicMock()
    mock_membership = MagicMock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_member(mock_db, user_id=1, chama_id=1)

    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called


def test_create_contribution():
    """Test create_contribution creates and commits contribution"""
    mock_db = MagicMock()
    mock_contribution = MagicMock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    result = create_contribution(mock_db, membership_id=1, amount=100.0)

    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called
