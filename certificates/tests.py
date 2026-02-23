import os
import calendar
import hashlib
import tempfile
import pandas as pd
from io import BytesIO
from PIL import Image

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from fpdf import FPDF
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from PyPDF2 import PdfReader

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import gettext_lazy as _

from certificates.models import Certificate
from certificates.utils import clean_string, build_role, make_pdf_of_certificate, validate_csv, certificate_create, format_certificate_date
from certificates.forms import UploadForm, CertificateForm, ValidateForm

from events.models import Event

from users.models import User, Participant


class CertificateViewsTest(TestCase):
    def setUp(self):
        self.username = "Test Username"
        self.password = "Test Password"
        self.participant_username = "Test Participant Username"

        content_type = ContentType.objects.get_for_model(Certificate)
        event_content_type = ContentType.objects.get_for_model(Event)

        self.add_permission = Permission.objects.get(codename="add_certificate", name="Can add certificate", content_type=content_type)
        self.delete_permission = Permission.objects.get(codename="delete_certificate", name="Can delete certificate", content_type=content_type)
        self.change_permission = Permission.objects.get(codename="change_certificate", name="Can change certificate", content_type=content_type)
        self.view_event_permission = Permission.objects.get(codename="view_event", content_type=event_content_type)
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        self.background = "Test Background.png"
        self.participant = Participant.objects.create(participant_username=self.participant_username)
        self.certificate = Certificate.objects.create(event=self.event,
                                                      username=self.participant,
                                                      background=self.background)

        self.user.user_permissions.add(self.add_permission)
        self.user.user_permissions.add(self.delete_permission)
        self.user.user_permissions.add(self.change_permission)
        self.user.user_permissions.add(self.view_event_permission)
        self.client.login(username=self.username, password=self.password)

    def test_certificate_create_manually_without_existing_certificates_redirects_to_bulk_upload(self):
        Certificate.objects.all().delete()
        url = reverse("events:event_certificate_manually", kwargs={"event_id": self.event.id})
        response = self.client.get(url)
        self.assertRedirects(response, reverse("events:event_certificate", kwargs={"event_id": self.event.id}))

    def test_certificate_create_manually_with_existing_certificates_get_method_returns_template(self):
        url = reverse("events:event_certificate_manually", kwargs={"event_id": self.event.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_create.html")

    def test_certificate_create_manually_with_existing_certificates_post_method_with_invalid_form_returns_template(self):
        url = reverse("events:event_certificate_manually", kwargs={"event_id": self.event.id})
        data = {
            "name": "Test Name",
            "username": self.participant.participant_username,
            "pronoun": "q", # wrong pronoun choice
            "hours": "02h09",
            "role": "ouvinte"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_create.html")

    def test_certificate_create_manually_with_existing_certificates_post_method_with_valid_form_creates_certificates(self):
        url = reverse("events:event_certificate_manually", kwargs={"event_id": self.event.id})
        data = {
            "name": "Test Name",
            "username_string": self.participant.participant_username,
            "pronoun": "o",
            "hours": "02h09",
            "role": "ouvinte"
        }
        self.assertEqual(Certificate.objects.count(), 1)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Certificate.objects.count(), 2)

    def test_certificate_create_manually_for_a_non_existent_event_fails(self):
        url = reverse("events:event_certificate_manually", kwargs={"event_id": 99999})
        data = {
            "name": "Test Name",
            "username": self.participant.participant_username,
            "pronoun": "o",
            "hours": "02h09",
            "role": "ouvinte"
        }

        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(url, data)

    def test_certificate_update_get_method_renders_proper_template(self):
        url = reverse("events:certificate_update", kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_update.html")

    def test_certificate_update_post_method_with_invalid_form_renders_proper_template(self):
        url = reverse("events:certificate_update", kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})
        data = {
            "name": "Test Name",
            "username": self.participant.participant_username,
            "pronoun": "q",  # wrong pronoun choice
            "hours": "02h09",
            "role": "ouvinte"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_update.html")

    def test_certificate_update_post_method_with_valid_form_updates_it_and_redirects(self):
        url = reverse("events:certificate_update", kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})
        data = {
            "name": "Test Name",
            "username_string": self.participant.participant_username,
            "pronoun": "a",
            "hours": "02h09",
            "role": "ouvinte"
        }
        self.assertEqual(self.certificate.pronoun, "o")
        response = self.client.post(url, data)

        self.certificate.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.certificate.pronoun, "a")

    def test_certificate_update_post_method_creates_new_participant_if_none_exists(self):
        data = {
            "name": "Test Name",
            "username_string": self.participant.participant_username + " (New)",
            "pronoun": "a",
            "hours": "02h09",
            "role": "ouvinte",
            "with_hours": "10h53"
        }
        url = reverse("events:certificate_update", kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})
        response = self.client.post(url, data)

        self.assertRedirects(response, reverse("events:event_detail", kwargs={"event_id": self.event.id}))

        self.certificate.refresh_from_db()
        participant = Participant.objects.get(participant_username="Test Participant Username (New)")

        self.assertEqual(self.certificate.username, participant)
        self.assertEqual(participant.participant_full_name, "Test Name")
        self.assertEqual(participant.created_by, self.user)
        self.assertEqual(participant.modified_by, self.user)

    def test_certificate_update_for_a_non_existent_event_fails (self):
        url = reverse("events:certificate_update", kwargs={"event_id": 9999, "certificate_id": self.certificate.id})
        data = {
            "name": "Test Name",
            "username": self.participant.participant_username,
            "pronoun": "o",
            "hours": "02h09",
            "role": "ouvinte"
        }

        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(url, data)

    def test_certificate_update_for_a_non_existent_certificate_fails (self):
        url = reverse("events:certificate_update", kwargs={"event_id": self.event.id, "certificate_id": 9999})
        data = {
            "name": "Test Name",
            "username": self.participant.participant_username,
            "pronoun": "o",
            "hours": "02h09",
            "role": "ouvinte"
        }

        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(url, data)

    def test_certificate_delete_get_method_renders_proper_template(self):
        url = reverse("events:certificate_delete", kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_delete.html")

    def test_certificate_delete_post_method_deletes_certificate_and_redirects(self):
        url = reverse("events:certificate_delete",
                      kwargs={"event_id": self.event.id, "certificate_id": self.certificate.id})

        self.assertEqual(Certificate.objects.count(), 1)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Certificate.objects.count(), 0)

    def test_certificate_delete_for_a_non_existent_event_fails (self):
        url = reverse("events:certificate_delete", kwargs={"event_id": 9999, "certificate_id": self.certificate.id})
        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(url)

    def test_certificate_delete_for_a_non_existent_certificate_fails (self):
        url = reverse("events:certificate_delete", kwargs={"event_id": self.event.id, "certificate_id": 9999})

        with self.assertRaises(ObjectDoesNotExist):
            self.client.post(url)

    def test_certificate_list_for_participant_without_certificates_returns_empty_list_in_context(self):
        url = reverse("certificates:certificate_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_list.html")
        self.assertQuerySetEqual(response.context["certificates"], [])

    def test_certificate_list_for_participant_with_certificates_returns_queryset_in_context(self):
        self.participant.participant_username = self.user.username
        self.participant.save()

        url = reverse("certificates:certificate_list")
        response = self.client.get(url)

        expected_certificates = Certificate.objects.filter(username=self.participant)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_list.html")
        self.assertQuerySetEqual(response.context["certificates"], expected_certificates)

    def test_certificate_validate_get_method_renders_proper_template(self):
        url = reverse("certificates:certificate_validate")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_validate.html")

    def test_certificate_validate_post_method_renders_proper_template(self):
        certificate = Certificate.objects.create(name="Test Name", background=self.background, event=self.event, hours="02h29", role="ouvinte")
        self.assertTrue(Certificate.objects.filter(certificate_hash=certificate.certificate_hash).exists())

        url = reverse("certificates:certificate_validate")
        data = {"certificate_hash": certificate.certificate_hash}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_detail.html")

    def test_certificate_validate_post_method_without_passing_a_hash_fails (self):
        url = reverse("certificates:certificate_validate")

        with self.assertRaises(MultiValueDictKeyError):
            self.client.post(url)

    def test_certificate_validate_post_method_with_certificate_that_is_not_found_by_hash_renders_proper_template(self):
        certificate = Certificate.objects.create(name="Test Name", background=self.background, event=self.event, hours="02h29", role="ouvinte")
        self.assertTrue(Certificate.objects.filter(certificate_hash=certificate.certificate_hash).exists())

        certificate_hash = "Test Certificate Hash"
        url = reverse("certificates:certificate_validate")
        data = {"certificate_hash": certificate_hash}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "certificates/certificate_validate.html")


def generate_valid_image():
    image = Image.new("RGB", (100, 100), color="white")
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    image.save(temp_file, format="JPEG")
    temp_file.seek(0)
    return SimpleUploadedFile("background.jpg", temp_file.read(), content_type="image/jpeg")


class CertificateDownloadByHashTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="admin")
        self.participant = Participant.objects.create(participant_username="johndoe")
        self.event = Event.objects.create(event_name="Test Event", date_start=date(2024, 1, 1))
        self.fake_image = self.fake_image = generate_valid_image()

        self.certificate = Certificate.objects.create(
            name="Test Name",
            username=self.participant,
            pronoun="O",
            event=self.event,
            hours="10h30",
            with_hours=True,
            role="ouvinte",
            background=self.fake_image,
            emitted_by=self.user,
        )

    def test_download_by_hash_of_existing_certificate(self):
        url = reverse("certificates:download_by_hash", kwargs={"certificate_hash":self.certificate.certificate_hash})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_download_by_hash_of_non_existing_certificate_redirects(self):
        url = reverse("certificates:download_by_hash", kwargs={"certificate_hash":"qwertyuiopasdfghjklzxcvbnm"})
        response = self.client.get(url)

        expected_redirect_url = reverse("certificates:certificate_validate")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_redirect_url)

class CertificateUtilsTest(TestCase):
    def test_clean_string_with_string_with_invalid_characters(self):
        test_string = "Teste: String? wi*th spe<cial charac|ters"
        expected_string = "Teste String with special characters"

        response = clean_string(test_string)
        self.assertEqual(response, expected_string)

    def test_clean_string_with_string_without_invalid_characters(self):
        test_string = "Teste String without special characters"
        expected_string = "Teste String without special characters"

        response = clean_string(test_string)
        self.assertEqual(response, expected_string)

    def test_build_role_for_participants(self):
        test_string = _("participant")
        expected_string = ""

        response = build_role(test_string)
        self.assertEqual(response, expected_string)

    def test_build_role_for_other_roles(self):
        test_string = "organizador"
        expected_string = " como organizador"

        response = build_role(test_string)
        self.assertEqual(response, expected_string)

    def test_format_certificate_date_same_date(self):
        date_start = date(2024, 1, 1)
        date_end = date(2024, 1, 1)
        expected_string = _("on {m_start} {d_start}, {y_start}").format(d_start=date_start.day,
                                                                        m_start=calendar.month_name[date_start.month],
                                                                        y_start=date_start.year)
        response = format_certificate_date(date_start, date_end)
        self.assertEqual(response, expected_string)

    def test_format_certificate_date_different_date_same_year_different_month(self):
        date_start = date(2024, 1, 1)
        date_end = date(2024, 2, 1)
        expected_string = _("from {m_start} {d_start} to {m_end} {d_end}, {y_start}").format(d_start=date_start.day,
                                                                                             m_start=calendar.month_name[date_start.month],
                                                                                             y_start=date_start.year,
                                                                                             d_end=date_end.day,
                                                                                             m_end=calendar.month_name[date_end.month])
        response = format_certificate_date(date_start, date_end)
        self.assertEqual(response, expected_string)

    def test_format_certificate_date_different_date_same_year_and_month(self):
        date_start = date(2024, 1, 1)
        date_end = date(2024, 1, 31)
        expected_string = _("from {m_start} {d_start} to {d_end}, {y_start}").format(d_start=date_start.day,
                                                                                     m_start=calendar.month_name[date_start.month],
                                                                                     y_start=date_start.year,
                                                                                     d_end=date_end.day)
        response = format_certificate_date(date_start, date_end)
        self.assertEqual(response, expected_string)

    def test_format_certificate_date_different_date_different_year(self):
        date_start = date(2024, 1, 1)
        date_end = date(2025, 12, 31)
        expected_string = _("from {m_start} {d_start}, {y_start} to {m_end} {d_end}, {y_end}").format(d_start=date_start.day,
                                                                                                      m_start=calendar.month_name[date_start.month],
                                                                                                      y_start=date_start.year,
                                                                                                      d_end=date_end.day,
                                                                                                      m_end=calendar.month_name[date_end.month],
                                                                                                      y_end=date_end.year)
        response = format_certificate_date(date_start, date_end)
        self.assertEqual(response, expected_string)

    def test_validate_csv_with_no_errors(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        errors = validate_csv(df)
        self.assertFalse(errors, [])

    def test_validate_csv_with_empty_data(self):
        df = pd.DataFrame(columns=["name","username","pronoun","hours","role"])
        errors = validate_csv(df)
        self.assertEqual(errors, [_("Your CSV file is empty. Verify and submit again")])

    def test_validate_csv_with_error_in_name_with_null_value(self):
        data = {
            "name": ["Test Name 1", ""],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Name invalid! Verify row 2, column 'name'", errors)

    def test_validate_csv_with_error_in_name_with_non_string_value(self):
        data = {
            "name": [1, "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Name invalid! Verify row 1, column 'name'", errors)

    def test_validate_csv_with_error_in_pronoun_with_null_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", ""],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Pronoun invalid! Verify row 2, column 'pronoun'", errors)

    def test_validate_csv_with_error_in_pronoun_with_non_string_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": [1, "A"],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Pronoun invalid! Verify row 1, column 'pronoun'", errors)

    def test_validate_csv_with_error_in_pronoun_with_invalid_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "G"],
            "hours": ["02h29", "03h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Pronoun invalid! Verify row 2, column 'pronoun'", errors)

    def test_validate_csv_with_error_in_hours_with_null_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", ""],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Hours invalid! Verify row 2, column 'hours'", errors)

    def test_validate_csv_with_error_in_hours_with_non_string_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": [3, "02h30"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Hours invalid! Verify row 1, column 'hours'", errors)

    def test_validate_csv_with_error_in_hours_with_invalid_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "duas horas e vinte nove minutos"],
            "role": ["ouvinte", "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Hours invalid! Verify row 2, column 'hours'", errors)

    def test_validate_csv_with_error_in_role_with_null_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "02h30"],
            "role": ["ouvinte", ""]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Role invalid! Verify row 2, column 'role'", errors)

    def test_validate_csv_with_error_in_role_with_non_string_value(self):
        data = {
            "name": ["Test Name 1", "Test Name 2"],
            "username": ["Test Username 1", "Test Username 2"],
            "pronoun": ["O", "A"],
            "hours": ["02h29", "02h30"],
            "role": [2, "palestrante"]
        }

        df = pd.DataFrame(data)
        df.replace('', pd.NA, inplace=True)
        errors = validate_csv(df)
        self.assertIn("Role invalid! Verify row 1, column 'role'", errors)

    def test_certificate_create_with_valid_form_succeeds_in_create_certificate(self):
        event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        background = "Test Background.png"
        username = "Test Username"
        password = "Test Password"
        emitted_by = User.objects.create_user(username=username, password=password)
        participant = Participant.objects.create(participant_full_name="Test Name", participant_username="Test Username")
        data = {
            "name": "Test Name",
            "username_string": participant.participant_username,
            "pronoun": "O",
            "event": event,
            "hours": "02h29",
            "role": "ouvinte",
        }

        self.assertEqual(Certificate.objects.count(), 0)
        certificate_create(data, event, background, emitted_by)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_certificate_create_with_valid_form_succeeds_in_create_certificate_and_updates_full_name(self):
        event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        background = "Test Background.png"
        username = "Test Username"
        password = "Test Password"
        emitted_by = User.objects.create_user(username=username, password=password)
        participant = Participant.objects.create(participant_username="Test Username")
        data = {
            "name": "Test Name",
            "username_string": participant.participant_username,
            "pronoun": "O",
            "event": event,
            "hours": "02h29",
            "role": "ouvinte",
        }

        self.assertEqual(Certificate.objects.count(), 0)
        self.assertEqual(Participant.objects.first().participant_full_name, "")
        certificate_create(data, event, background, emitted_by)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(Participant.objects.first().participant_full_name, "Test Name")

    def test_certificate_create_with_valid_form_without_username_succeeds_in_create_certificate(self):
        event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        background = "Test Background.png"
        username = "Test Username"
        password = "Test Password"
        emitted_by = User.objects.create_user(username=username, password=password)
        data = {
            "name": "Test Name",
            "username_string": "",
            "pronoun": "O",
            "event": event,
            "hours": "02h29",
            "role": "ouvinte",
        }

        self.assertEqual(Certificate.objects.count(), 0)
        certificate = certificate_create(data, event, background, emitted_by)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_certificate_create_with_valid_form_with_older_participant_succeeds_in_create_certificate(self):
        event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        background = "Test Background.png"
        username = "Test Username"
        password = "Test Password"
        emitted_by = User.objects.create_user(username=username, password=password)

        participant = Participant.objects.create(participant_full_name="Test Name 2", participant_username="Test Username")
        data = {
            "name": "Test Name",
            "username_string": participant.participant_username,
            "pronoun": "O",
            "event": event,
            "hours": "02h29",
            "role": "ouvinte",
        }

        self.assertEqual(Certificate.objects.count(), 0)
        certificate = certificate_create(data, event, background, emitted_by)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertIsNotNone(certificate.username)

    def mock_structure(self, mock_image, certificate_name, expected_name):
        event = MagicMock()
        event.__str__.return_value = "Test Event"
        event.date_start = date(2024, 1, 1)
        event.date_end = date(2024, 12, 31)

        file_mock = MagicMock(spec=File, name='FileMock')
        file_mock.name = 'test1.jpg'
        file_mock.path = '/media/test1.jpg'

        certificate = MagicMock(role=_('participant'),
                                background=file_mock,
                                hours="05h00",
                                event=event)
        certificate.configure_mock(name=certificate_name)

        pdf = make_pdf_of_certificate(certificate)

        mock_image.assert_any_call('/media/test1.jpg', x=0, y=0, w=297, h=210)
        image_path = os.path.join(settings.BASE_DIR, 'static', 'images', settings.VALERIOS_SIGNATURE)
        mock_image.assert_any_call(image_path, x=131, y=95, w=35, h=16)

        pdf_output = pdf.output(dest='S').encode('latin-1')
        pdf_bytes = BytesIO(pdf_output)
        pdf_reader = PdfReader(pdf_bytes)
        pdf_content = pdf_reader.pages[0].extract_text()

        self.assertIsInstance(pdf, FPDF)
        self.assertIn('CERTIFICATE', pdf_content)
        self.assertIn(expected_name, pdf_content)
        self.assertIn('Test Event', pdf_content)
        self.assertIn('05h00', pdf_content)

    @patch('certificates.utils.settings.VALERIOS_SIGNATURE', 'fake_signature.png')
    @patch('certificates.utils.settings.ERICAS_SIGNATURE', 'fake_signature2.png')
    @patch('certificates.utils.FPDF.image')
    def test_make_pdf_of_certificate(self, mock_image):
        certificate_name = expected_name = "Mock Name"
        self.mock_structure(mock_image, certificate_name, expected_name)

    @patch('certificates.utils.settings.VALERIOS_SIGNATURE', 'fake_signature.png')
    @patch('certificates.utils.settings.ERICAS_SIGNATURE', 'fake_signature2.png')
    @patch('certificates.utils.FPDF.image')
    def test_make_pdf_of_certificate_with_participant_with_long_name(self, mock_image):
        certificate_name = "Mock Name"*66
        expected_name = "Mock " + "N. "*65 + "Name"

        self.mock_structure(mock_image, certificate_name, expected_name)


class UploadFormTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(event_name="Sample Event", date_start=date(2024, 1, 1))
        self.valid_csv_file = SimpleUploadedFile("test.csv", b"sample,csv,data", content_type="text/csv")
        self.valid_image_file = SimpleUploadedFile("background.png", b"binarydata", content_type="image/png")
        self.invalid_csv_file = SimpleUploadedFile("test.txt", b"text data", content_type="text/plain")
        self.invalid_image_file = SimpleUploadedFile("background.jpeg", b"binarydata", content_type="image/jpeg")
        self.form_data = {"certificate_event": self.event.id}

    def test_form_valid_data(self):
        form_files = {"certificate_csv": self.valid_csv_file, "certificate_background": self.valid_image_file}
        form = UploadForm(data=self.form_data, files=form_files)
        self.assertTrue(form.is_valid())

    def test_form_missing_files(self):
        form_files = {}
        form = UploadForm(data=self.form_data, files=form_files)
        self.assertFalse(form.is_valid())
        self.assertIn("certificate_csv", form.errors)
        self.assertIn("certificate_background", form.errors)

    def test_form_invalid_file_type_for_csv(self):
        form_files = {"certificate_csv": self.invalid_csv_file,"certificate_background": self.valid_image_file}
        form = UploadForm(data=self.form_data, files=form_files)
        self.assertFalse(form.is_valid())

    def test_form_invalid_file_type_for_jpeg(self):
        form_files = {"certificate_csv": self.valid_csv_file,"certificate_background": self.invalid_image_file}
        form = UploadForm(data=self.form_data, files=form_files)
        self.assertFalse(form.is_valid())

    def test_form_empty_file(self):
        empty_file = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        form_files = {"certificate_csv": empty_file,"certificate_background": self.valid_image_file}
        form = UploadForm(data=self.form_data, files=form_files)
        self.assertFalse(form.is_valid())
        self.assertIn("certificate_csv", form.errors)


class CertificateFormTests(TestCase):
    def setUp(self):
        self.participant_username = "Test Participant Username"
        self.participant_full_name = "Test Participant Name"
        self.participant = Participant.objects.create(participant_full_name=self.participant_full_name, participant_username=self.participant_username)
        self.valid_data = {
            "name": "Test Name",
            "username": self.participant,
            "pronoun": "o",
            "hours": "10h30",
            "role": "ouvinte",
            "with_hours": "true"
        }

    def test_form_valid_data(self):
        form = CertificateForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_missing_name(self):
        data = self.valid_data.copy()
        data["name"] = ""
        form = CertificateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_clean_name_strips_whitespace(self):
        data = self.valid_data.copy()
        data["name"] = "  John Doe  "
        form = CertificateForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "John Doe")

    def test_form_clean_role_default(self):
        data = self.valid_data.copy()
        data["role"] = ""
        form = CertificateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("This field is required."), form.errors["role"])

    def test_form_clean_role_strips_whitespace(self):
        data = self.valid_data.copy()
        data["role"] = "participant"
        form = CertificateForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["role"], _("participant"))

    def test_form_clean_hours_strips_whitespace(self):
        data = self.valid_data.copy()
        data["hours"] = " 10h30 "
        form = CertificateForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["hours"], "10h30")

    def test_form_clean_pronoun_default(self):
        data = self.valid_data.copy()
        data["pronoun"] = ""
        form = CertificateForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("This field is required."), form.errors["pronoun"])

    def test_widgets_attributes(self):
        form = CertificateForm()
        self.assertEqual(form.fields['name'].widget.attrs['placeholder'], _("Enter the real name of the individual"))
        self.assertEqual(form.fields['hours'].widget.attrs['placeholder'], _("Hours worked in the event by the individual. Format: (HHhMM)"))
        self.assertEqual(form.fields['role'].widget.attrs['placeholder'], _("Role of the individual in the event"))


class ValidateFormTest(TestCase):
    def test_form_valid_with_valid_data(self):
        form_data = {'certificate_hash': 'abc123'}
        form = ValidateForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_with_empty_data(self):
        form_data = {}
        form = ValidateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('certificate_hash', form.errors)
        self.assertEqual(form.errors['certificate_hash'][0], _('This field is required.'))

    def test_form_invalid_with_blank_certificate_hash(self):
        form_data = {'certificate_hash': ''}
        form = ValidateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('certificate_hash', form.errors)
        self.assertEqual(form.errors['certificate_hash'][0], _('This field is required.'))

    def test_form_invalid_with_whitespace_only_certificate_hash(self):
        form_data = {'certificate_hash': '   '}
        form = ValidateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('certificate_hash', form.errors)
        self.assertEqual(form.errors['certificate_hash'][0], _('This field is required.'))

    def test_form_accepts_long_certificate_hash(self):
        long_hash = 'a' * 500
        form_data = {'certificate_hash': long_hash}
        form = ValidateForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_with_too_long_certificate_hash(self):
        long_hash = 'a' * 501
        form_data = {'certificate_hash': long_hash}
        form = ValidateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('certificate_hash', form.errors)
        self.assertEqual(form.errors['certificate_hash'][0], _('Ensure this field has at most 256 characters.'))


class CertificateModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(username="testuser", email="test@example.com")
        self.event = Event.objects.create(event_name="Test Event", date_start=date(2024,1,1))
        self.participant = Participant.objects.create(participant_username="participant1")
        self.uploaded_file = SimpleUploadedFile(
            name='background.jpg',
            content=b'some image content',
            content_type='image/jpeg'
        )

    def test_certificate_creation(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            username=self.participant,
            pronoun="a",
            event=self.event,
            hours="10h30",
            role="speaker",
            background=self.uploaded_file,
            emitted_by=self.user
        )
        self.assertEqual(certificate.name, "John Doe")
        self.assertEqual(certificate.username, self.participant)
        self.assertEqual(certificate.pronoun, "a")
        self.assertEqual(certificate.event, self.event)
        self.assertEqual(certificate.hours, "10h30")
        self.assertEqual(certificate.role, "speaker")
        self.assertEqual(certificate.emitted_by, self.user)
        self.assertIsNotNone(certificate.certificate_hash)

    def test_certificate_hash_generation(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            event=self.event,
            hours="10h30",
            role="speaker",
            background=self.uploaded_file
        )
        expected_hash = hashlib.sha1(
            b"Certificate John DoeTest Event10h30speaker"
        ).hexdigest()
        self.assertEqual(certificate.certificate_hash, expected_hash)

    def test_certificate_str_with_username(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            username=self.participant,
            event=self.event,
            hours="10h30",
            role="speaker",
            background=self.uploaded_file
        )
        expected_str = f"{self.event} - {self.participant}"
        self.assertEqual(str(certificate), expected_str)

    def test_certificate_str_without_username(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            event=self.event,
            hours="10h30",
            role="speaker",
            background=self.uploaded_file
        )
        expected_str = f"{self.event} - John Doe"
        self.assertEqual(str(certificate), expected_str)

    def test_default_pronoun(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            event=self.event,
            hours="10h30",
            role="speaker",
            background=self.uploaded_file
        )
        self.assertEqual(certificate.pronoun, "o")

    def test_hours_validator_valid_input(self):
        certificate = Certificate.objects.create(
            name="John Doe",
            event=self.event,
            hours="02h29",
            role="speaker",
            background=self.uploaded_file
        )
        self.assertEqual(certificate.hours, "02h29")

    def test_hours_validator_invalid_input(self):
        with self.assertRaises(Exception):
            certificate = Certificate(
                name="John Doe",
                event=self.event,
                hours="02 hours and 29 minutes",
                role="speaker",
                background=self.uploaded_file
            )
            certificate.full_clean()
