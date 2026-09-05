from .models import Address


def set_default_address(address):
    """Make `address` the user's only default."""
    Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)
    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
    return address


def ensure_default_address(address):
    """Give a user their first address as the default automatically."""
    has_other = Address.objects.filter(user=address.user).exclude(pk=address.pk).exists()
    if not has_other:
        return set_default_address(address)
    if address.is_default:
        return set_default_address(address)
    return address
