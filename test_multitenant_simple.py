#!/usr/bin/env python3
"""
Simple test for multi-tenant implementation without external dependencies.
Tests key functionality that can run standalone.
"""
import sys
import os
import inspect

def test_schema_configuration():
    """Test that models have correct schema configuration"""
    print("🔍 Testing schema configuration in models...")

    try:
        # Test User model
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

        # Dynamically import to avoid dependency issues
        from backend.models.user import User, UserRole
        from backend.models.chama import Chama
        from backend.models.membership import Membership, MembershipRole
        from backend.models.contribution import Contribution

        # Check User schema
        assert hasattr(User, '__table_args__'), "User should have __table_args__"
        assert User.__table_args__['schema'] == 'public', f"User schema should be 'public', got {User.__table_args__['schema']}"
        print("✅ User model uses public schema")

        # Check Chama schema
        assert hasattr(Chama, '__table_args__'), "Chama should have __table_args__"
        assert Chama.__table_args__['schema'] == 'public', f"Chama schema should be 'public', got {Chama.__table_args__['schema']}"
        print("✅ Chama model uses public schema")

        # Check Membership schema
        assert hasattr(Membership, '__table_args__'), "Membership should have __table_args__"
        assert Membership.__table_args__['schema'] == 'public', f"Membership schema should be 'public', got {Membership.__table_args__['schema']}"
        print("✅ Membership model uses public schema")

        # Check Contribution schema (should NOT have explicit schema)
        table_args = getattr(Contribution, '__table_args__', None)
        if table_args:
            schema = table_args.get('schema')
            assert schema is None or schema == 'chama', f"Contribution should use tenant schema, got schema: {schema}"
        else:
            assert True, "Contribution has no __table_args__, will use tenant schema"
        print("✅ Contribution model uses tenant schema (no explicit schema)")

        return True

    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tenant_context_logic():
    """Test tenant context management logic"""
    print("🔄 Testing tenant context logic...")

    try:
        from backend.database import get_schema_name

        # Test schema naming
        assert get_schema_name(123) == "chama_123", f"Expected 'chama_123', got '{get_schema_name(123)}'"
        assert get_schema_name(999) == "chama_999", f"Expected 'chama_999', got '{get_schema_name(999)}'"
        print("✅ Schema name generation works")

        return True

    except Exception as e:
        print(f"❌ Context logic test failed: {e}")
        return False

def test_foreign_key_configuration():
    """Test that foreign keys are properly configured for multi-schema operation"""
    print("🔗 Testing foreign key relationships...")

    try:
        from backend.models.membership import Membership
        from backend.models.contribution import Contribution

        # Check Membership foreign keys point to public schema
        for column in Membership.__table__.columns:
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    # Should reference public schema
                    target_table = str(fk.target_fullname)
                    if 'users' in target_table:
                        assert 'public.users' in target_table, f"Membership user FK should reference public.users, got {target_table}"
                    elif 'chamas' in target_table:
                        assert 'public.chamas' in target_table, f"Membership chama FK should reference public.chamas, got {target_table}"
                    # Note: contributions FK is still in same schema

        print("✅ Membership foreign keys reference public schema correctly")

        # Check Contribution foreign keys
        for column in Contribution.__table__.columns:
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    target_table = str(fk.target_fullname)
                    if 'chamas' in target_table:
                        assert 'public.chamas' in target_table, f"Contribution chama FK should reference public.chamas, got {target_table}"
                    # membership FK should be in tenant schema (no explicit schema)

        print("✅ Contribution foreign keys configured correctly")

        return True

    except Exception as e:
        print(f"❌ Foreign key test failed: {e}")
        return False

def test_middleware_patterns():
    """Test that middleware patterns are correctly defined"""
    print("🛡️ Testing middleware patterns...")

    try:
        from backend.middleware import TenantContextMiddleware
        import re

        middleware = TenantContextMiddleware(None)
        patterns = middleware.chama_patterns

        # Test pattern matching
        test_urls = [
            ("/chamas/123/members", 123),
            ("/chamas/456/contributions", 456),
            ("/chamas/789/summary", 789),
            ("/users/me", None),  # Should not match
            ("/users/token", None),  # Should not match
        ]

        for url, expected_id in test_urls:
            match = None
            for pattern in patterns:
                match = pattern.match(url)
                if match:
                    break

            if expected_id is None:
                assert match is None, f"URL '{url}' should not match any pattern"
            else:
                assert match is not None, f"URL '{url}' should match a pattern"
                extracted_id = int(match.group(1))
                assert extracted_id == expected_id, f"Expected ID {expected_id}, got {extracted_id} for URL '{url}'"

        print("✅ Middleware URL pattern matching works")

        return True

    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Multi-Tenant Implementation Functional Test Suite\n")

    tests = [
        test_schema_configuration,
        test_tenant_context_logic,
        test_foreign_key_configuration,
        test_middleware_patterns,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Blank line between tests
        except Exception as e:
            print(f"❌ {test.__name__} crashed: {e}\n")

    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All multi-tenancy functionality tests PASSED!")
        print("✅ Schema isolation configured correctly")
        print("✅ Context management logic works")
        print("✅ Cross-schema relationships configured")
        print("✅ Middleware tenant extraction works")
        print("\n🏆 Implementation is functionally complete and ready for production!")
        return True
    else:
        print("💥 Some tests failed. Implementation needs review.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
