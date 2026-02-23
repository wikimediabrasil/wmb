from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from credentials.models import Credential
from credentials.forms import CredentialForm

User = get_user_model()
class CredentialViewsTests(TestCase):

    def setUp(self):
        # Users
        self.user = User.objects.create_user(
            username="user",
            password="pass123"
        )

        self.admin = User.objects.create_user(
            username="admin",
            password="pass123"
        )

        # Assign all credential permissions to admin
        permissions = Permission.objects.filter(
            content_type__app_label="credentials"
        )
        self.admin.user_permissions.set(permissions)

        # Sample credential (all required fields!)
        self.credential = Credential.objects.create(
            username="TestUser",
            full_name="Test User",
            event="Test Event",
            verification_code="ABC123",
            issued_by=self.admin,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=10),
            photograph="https://example.com/photo.jpg",
        )

    # ------------------------
    # LIST
    # ------------------------

    def test_credential_list_without_permission_redirects(self):
        self.client.login(username="user", password="pass123")
        response = self.client.get(reverse("credentials:credential_list"))
        self.assertRedirects(
            response,
            reverse("credentials:credential_validate")
        )

    def test_credential_list_with_permission(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(reverse("credentials:credential_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestUser")

    # ------------------------
    # DETAIL
    # ------------------------

    def test_detail_requires_permission(self):
        self.client.login(username="user", password="pass123")
        response = self.client.get(
            reverse("credentials:credential_detail",
                    kwargs={"verification_code": "ABC123"})
        )
        self.assertEqual(response.status_code, 403)

    def test_detail_success(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse("credentials:credential_detail",
                    kwargs={"verification_code": "ABC123"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestUser")

    def test_detail_404(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse("credentials:credential_detail",
                    kwargs={"verification_code": "INVALID"})
        )
        self.assertEqual(response.status_code, 404)

    # ------------------------
    # CREATE
    # ------------------------

    @patch("credentials.views.shorten_url")
    def test_create_get(self, mock_shorten):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(reverse("credentials:credential_create"))
        self.assertEqual(response.status_code, 200)

    @patch("credentials.views.shorten_url")
    def test_create_post_valid(self, mock_shorten):
        mock_shorten.return_value = "https://short.url/test"

        self.client.login(username="admin", password="pass123")

        response = self.client.post(
            reverse("credentials:credential_create"),
            {
                "username": "NewUser",
                "full_name": "New User",
                "event": "New Event",
                "photograph": "https://example.com/photo.jpg",
                "valid_from": date.today(),
                "valid_until": date.today() + timedelta(days=5),
            },
        )

        self.assertEqual(response.status_code, 302)

        credential = Credential.objects.get(username="NewUser")
        self.assertEqual(credential.issued_by, self.admin)

    @patch("credentials.views.shorten_url")
    def test_create_post_invalid(self, mock_shorten):
        self.client.login(username="admin", password="pass123")

        response = self.client.post(
            reverse("credentials:credential_create"),
            {}
        )

        self.assertEqual(response.status_code, 200)

    # ------------------------
    # UPDATE
    # ------------------------

    def test_update_get(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse("credentials:credential_update",
                    kwargs={"verification_code": "ABC123"})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_post_valid(self):
        self.client.login(username="admin", password="pass123")

        response = self.client.post(
            reverse("credentials:credential_update",
                    kwargs={"verification_code": "ABC123"}),
            {
                "username": "UpdatedUser",
                "full_name": "Updated Name",
                "event": "Test Event",
                "photograph": "https://example.com/photo.jpg",
                "valid_from": date.today(),
                "valid_until": date.today() + timedelta(days=5),
            },
        )

        self.assertRedirects(
            response,
            reverse("credentials:credential_detail",
                    kwargs={"verification_code": "ABC123"})
        )

    def test_update_post_invalid(self):
        self.client.login(username="admin", password="pass123")

        response = self.client.post(
            reverse("credentials:credential_update",
                    kwargs={"verification_code": "ABC123"}),
            {}
        )

        self.assertEqual(response.status_code, 200)

    # ------------------------
    # DELETE
    # ------------------------

    def test_delete_get(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.get(
            reverse("credentials:credential_delete",
                    kwargs={"verification_code": "ABC123"})
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_post(self):
        self.client.login(username="admin", password="pass123")
        response = self.client.post(
            reverse("credentials:credential_delete",
                    kwargs={"verification_code": "ABC123"})
        )

        self.assertRedirects(
            response,
            reverse("credentials:credential_list")
        )
        self.assertFalse(
            Credential.objects.filter(
                verification_code="ABC123"
            ).exists()
        )

    # ------------------------
    # VALIDATE
    # ------------------------

    def test_validate_get(self):
        response = self.client.get(reverse("credentials:credential_validate"))
        self.assertEqual(response.status_code, 200)

    def test_validate_invalid_code(self):
        response = self.client.post(
            reverse("credentials:credential_validate"),
            {"verification_code": "INVALID"}
        )

        self.assertContains(response, _("Invalid verification code."))

    def test_validate_expired(self):
        Credential.objects.create(
            username="ExpiredUser",
            full_name="Expired User",
            event="Expired Event",
            verification_code="EXPIRED",
            issued_by=self.admin,
            valid_from=date.today() - timedelta(days=10),
            valid_until=date.today() - timedelta(days=1),
            photograph="https://example.com/photo.jpg",
        )

        response = self.client.post(
            reverse("credentials:credential_validate"),
            {"verification_code": "EXPIRED"}
        )

        self.assertContains(
            response,
            _("This credential verification code has expired.")
        )

    def test_validate_success(self):
        response = self.client.post(
            reverse("credentials:credential_validate"),
            {"verification_code": "ABC123"}
        )

        self.assertContains(response, "TestUser")


class CredentialModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="issuer",
            password="pass123"
        )

    # ---------------------------------
    # SAVE + VERIFICATION CODE
    # ---------------------------------

    @patch("credentials.models.secrets.token_urlsafe")
    def test_save_generates_verification_code(self, mock_token):
        mock_token.return_value = "generated_code"

        credential = Credential.objects.create(
            username="TestUser",
            full_name="John Doe",
            event="Test Event",
        )

        self.assertEqual(credential.verification_code, "generated_code")

    def test_save_does_not_override_existing_verification_code(self):
        credential = Credential.objects.create(
            username="TestUser",
            full_name="John Doe",
            event="Test Event",
            verification_code="manual_code"
        )

        self.assertEqual(credential.verification_code, "manual_code")

    # ---------------------------------
    # WIKIMEDIA URL
    # ---------------------------------

    def test_get_wikimedia_profile_url(self):
        credential = Credential.objects.create(
            username="User Name",
            full_name="John Doe",
            event="Test Event",
        )

        url = credential.get_wikimedia_profile_url()
        self.assertEqual(
            url,
            "https://meta.wikimedia.org/wiki/User:User%20Name"
        )

    # ---------------------------------
    # MASKED CPF
    # ---------------------------------

    def test_masked_cpf_empty(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cpf=None
        )

        self.assertEqual(credential.masked_cpf(), "")

    def test_masked_cpf_11_digits(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cpf="12345678901"
        )

        self.assertEqual(
            credential.masked_cpf(),
            "***.456.789-**"
        )

    def test_masked_cpf_other_length(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cpf="12345"
        )

        self.assertEqual(
            credential.masked_cpf(),
            "*****"
        )

    # ---------------------------------
    # MASKED CIN
    # ---------------------------------

    def test_masked_cin_empty(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cin=None
        )

        self.assertEqual(credential.masked_cin(), "")

    def test_masked_cin_short(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cin="12"
        )

        self.assertEqual(
            credential.masked_cin(),
            "**"
        )

    def test_masked_cin_long(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Doe",
            event="Test Event",
            cin="ABCDEFGH"
        )

        self.assertEqual(
            credential.masked_cin(),
            "ABC*****"
        )

    # ---------------------------------
    # MASKED NAME
    # ---------------------------------

    def test_masked_name_empty(self):
        credential = Credential.objects.create(
            username="User",
            full_name="",
            event="Test Event",
        )

        self.assertEqual(credential.masked_name(), "")

    def test_masked_name_single(self):
        credential = Credential.objects.create(
            username="User",
            full_name="Plato",
            event="Test Event",
        )

        self.assertEqual(credential.masked_name(), "Plato")

    def test_masked_name_multiple(self):
        credential = Credential.objects.create(
            username="User",
            full_name="John Ronald Reuel",
            event="Test Event",
        )

        self.assertEqual(
            credential.masked_name(),
            "John R. R."
        )

    # ---------------------------------
    # __str__
    # ---------------------------------

    def test_str_representation(self):
        credential = Credential.objects.create(
            username="User123",
            full_name="John Doe",
            event="Wikimedia Summit",
        )

        self.assertEqual(
            str(credential),
            "Wikimedia Summit - User123"
        )


class CredentialFormTests(TestCase):

    def setUp(self):
        self.valid_data = {
            "username": "TestUser",
            "full_name": "John Doe",
            "cpf": "12345678901",
            "cin": "ABC123",
            "photograph": "https://example.com/photo.jpg",
            "event": "Test Event",
            "valid_from": date.today(),
            "valid_until": date.today() + timedelta(days=1),
        }

    # ---------------------------------
    # VALID FORM
    # ---------------------------------

    def test_form_valid(self):
        form = CredentialForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    # ---------------------------------
    # REQUIRED FIELDS
    # ---------------------------------

    def test_missing_required_fields(self):
        form = CredentialForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("full_name", form.errors)
        self.assertIn("photograph", form.errors)
        self.assertIn("event", form.errors)
        self.assertIn("valid_from", form.errors)
        self.assertIn("valid_until", form.errors)

    # ---------------------------------
    # DATE VALIDATION
    # ---------------------------------

    def test_valid_dates_equal(self):
        data = self.valid_data.copy()
        data["valid_until"] = data["valid_from"]

        form = CredentialForm(data=data)
        self.assertTrue(form.is_valid())

    def test_valid_until_before_valid_from(self):
        data = self.valid_data.copy()
        data["valid_until"] = data["valid_from"] - timedelta(days=1)

        form = CredentialForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("Valid until date cannot be before valid from date."),
            form.non_field_errors()
        )

    def test_missing_one_date(self):
        data = self.valid_data.copy()
        data.pop("valid_until")

        form = CredentialForm(data=data)
        self.assertFalse(form.is_valid())  # required=True in widget/model

    # ---------------------------------
    # EXCLUDED FIELDS
    # ---------------------------------

    def test_excluded_fields_not_in_form(self):
        form = CredentialForm()

        self.assertNotIn("verification_code", form.fields)
        self.assertNotIn("issued_at", form.fields)
        self.assertNotIn("issued_by", form.fields)
        self.assertNotIn("url", form.fields)

    # ---------------------------------
    # WIDGET ATTRIBUTES
    # ---------------------------------

    def test_widget_attributes(self):
        form = CredentialForm()

        self.assertEqual(
            form.fields["username"].widget.attrs["placeholder"],
            "Enter the username"
        )
        self.assertEqual(
            form.fields["photograph"].widget.input_type,
            "url"
        )
        self.assertEqual(
            form.fields["username"].widget.attrs["required"],
            "required"
        )