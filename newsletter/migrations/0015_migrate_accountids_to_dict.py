# Generated migration to convert accountIds from list to dict format
from django.db import migrations
from datetime import datetime


def migrate_accountids_forward(apps, schema_editor):
    """
    Convert accountIds from list format to dict format.
    
    Old format: ["accountId1", "accountId2"]
    New format: {
        "accountId1": {"active": True, "subscribed_at": "2024-01-01T00:00:00Z"},
        "accountId2": {"active": True, "subscribed_at": "2024-01-01T00:00:00Z"}
    }
    """
    Subscriber = apps.get_model('newsletter', 'Subscriber')
    migration_timestamp = datetime.utcnow().isoformat() + "Z"
    
    for subscriber in Subscriber.objects.all():
        account_ids = subscriber.accountIds
        
        # Skip if already in dict format or empty
        if isinstance(account_ids, dict):
            continue
        
        if isinstance(account_ids, list):
            # Convert list to dict
            new_account_ids = {}
            for account_id in account_ids:
                if account_id:  # Skip None or empty strings
                    new_account_ids[account_id] = {
                        "active": True,
                        "subscribed_at": subscriber.subscribed_on.isoformat() + "Z" if subscriber.subscribed_on else migration_timestamp,
                        "migrated_from_list": True
                    }
            subscriber.accountIds = new_account_ids
            subscriber.save()
        elif account_ids is None:
            # Initialize empty dict
            subscriber.accountIds = {}
            subscriber.save()


def migrate_accountids_backward(apps, schema_editor):
    """
    Revert accountIds from dict format back to list format.
    Note: This will lose the active status and timestamps.
    """
    Subscriber = apps.get_model('newsletter', 'Subscriber')
    
    for subscriber in Subscriber.objects.all():
        account_ids = subscriber.accountIds
        
        # Skip if already in list format or empty
        if isinstance(account_ids, list):
            continue
        
        if isinstance(account_ids, dict):
            # Convert dict to list (only active subscriptions)
            new_account_ids = [
                account_id for account_id, data in account_ids.items()
                if isinstance(data, dict) and data.get("active", True)
            ]
            subscriber.accountIds = new_account_ids
            subscriber.save()
        elif account_ids is None:
            subscriber.accountIds = []
            subscriber.save()


class Migration(migrations.Migration):

    dependencies = [
        ('newsletter', '0014_remove_subscriber_accountid_subscriber_accountids'),
    ]

    operations = [
        migrations.RunPython(
            migrate_accountids_forward,
            migrate_accountids_backward,
        ),
    ]

