from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Sign in with a username or an email address.

    Input containing "@" is matched first as an email, ignoring case, and
    then as a username, so legacy usernames with "@" in them still work.
    Sign-up now refuses "@" in usernames, so new accounts never collide.
    Anything else is matched as a username.

    Django's own checks are kept: an inactive user cannot sign in, and the
    password hasher runs even when nobody matches, so response timing does
    not reveal which accounts exist.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        user = self._find_user(username)
        if user is None:
            # Pay for one hash anyway, as ModelBackend does.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _find_user(self, username):
        User = get_user_model()
        if "@" in username:
            # The case-insensitive unique constraint allows at most one.
            user = User._default_manager.filter(email__iexact=username).first()
            if user is not None:
                return user
        try:
            return User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            return None
