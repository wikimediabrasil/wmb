import io
import calendar
import pandas as pd
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.templatetags.static import static
from django.template import Template, Context
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from certificates.forms import UploadForm
from certificates.models import Certificate
from events.models import Event
from events.forms import EventForm
from users.models import User, Participant


class EventModelTest(TestCase):
    def setUp(self):
        self.username = "Username"
        self.password = "Password"
        self.user = User.objects.create_user(self.username, self.password)

        self.add_permission = Permission.objects.get(codename="add_event", name="Can add event")
        self.delete_permission = Permission.objects.get(codename="delete_event", name="Can delete event")
        self.change_permission = Permission.objects.get(codename="change_event", name="Can change event")
        self.user.user_permissions.add(self.add_permission)
        self.user.user_permissions.add(self.delete_permission)
        self.user.user_permissions.add(self.change_permission)

        self.event_name = "Event Name"
        self.date_start = date(2024,1,1)
        self.date_end = date(2024, 12, 31)
        self.link = "https://www.link.com"
        self.created_by = self.user

        self.valid_data = {
            "event_name": self.event_name,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "link": self.link,
            "created_by": self.created_by,
        }

    def test_event_creation(self):
        event = Event.objects.create(**self.valid_data)
        self.assertEqual(event.event_name, self.event_name)
        self.assertEqual(event.date_start, self.date_start)
        self.assertEqual(event.date_end, self.date_end)
        self.assertEqual(event.link, self.link)
        self.assertEqual(event.created_by, self.created_by)
        self.assertEqual(event.created_on, date.today())

    def test_event_string_representation(self):
        event = Event.objects.create(**self.valid_data)
        self.assertEqual(str(event), self.event_name)

    def test_save_without_date_end(self):
        data = self.valid_data.copy()
        del data["date_end"]
        event = Event.objects.create(**data)
        self.assertEqual(event.date_end, event.date_start)

    def test_save_with_date_end(self):
        event_data_with_end_date = {**self.valid_data, 'date_end': date(2024, 12, 31)}
        event = Event.objects.create(**event_data_with_end_date)
        self.assertEqual(event.date_end, date(2024, 12, 31))

    def test_link_field(self):
        event_data_with_link = {**self.valid_data, 'link': 'https://example.com'}
        event = Event.objects.create(**event_data_with_link)
        self.assertEqual(event.link, 'https://example.com')

    def test_created_on_field(self):
        event = Event.objects.create(**self.valid_data)
        self.assertIsNotNone(event.created_on)
        self.assertEqual(event.created_on, event.created_on)  # Just checking that it's a valid date

    def test_event_created_by_optional(self):
        event_data_no_creator = {**self.valid_data, 'created_by': None}
        event = Event.objects.create(**event_data_no_creator)
        self.assertIsNone(event.created_by)

    def test_created_by_nullable(self):
        event = Event.objects.create(**self.valid_data)
        self.assertIsNotNone(event.created_by)
        self.assertEqual(event.created_by, self.user)

class EventViewsTest(TestCase):
    def setUp(self):
        self.username = "Username"
        self.password = "Password"
        self.user = User.objects.create_user(self.username, self.password)

        content_type = ContentType.objects.get_for_model(Certificate)
        self.add_certificate_permission = Permission.objects.get(codename="add_certificate", name="Can add certificate")
        self.delete_certificate_permission = Permission.objects.get(codename="delete_certificate", name="Can delete certificate")
        self.change_certificate_permission = Permission.objects.get(codename="change_certificate", name="Can change certificate")
        self.view_event_permission = Permission.objects.get(codename="view_event", name="Can view event")
        self.add_event_permission = Permission.objects.get(codename="add_event", name="Can add event")
        self.delete_event_permission = Permission.objects.get(codename="delete_event", name="Can delete event")
        self.change_event_permission = Permission.objects.get(codename="change_event", name="Can change event")
        self.download_certificates = Permission.objects.create(codename="download_all", name="Can download certificates from event", content_type=content_type)
        self.user.user_permissions.add(self.add_certificate_permission)
        self.user.user_permissions.add(self.delete_certificate_permission)
        self.user.user_permissions.add(self.change_certificate_permission)
        self.user.user_permissions.add(self.view_event_permission)
        self.user.user_permissions.add(self.add_event_permission)
        self.user.user_permissions.add(self.delete_event_permission)
        self.user.user_permissions.add(self.change_event_permission)
        self.user.user_permissions.add(self.download_certificates)

        self.client.force_login(self.user)

        self.event_name = "Event Name"
        self.date_start = date(2024,1,1)
        self.date_end = date(2024, 12, 31)
        self.link = "https://www.link.com"

        self.data = {
            "event_name": self.event_name,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "link": self.link
        }

    def test_event_create_get_view(self):
        response = self.client.get(reverse("events:event_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_create.html")
        self.assertIsInstance(response.context["form"], EventForm)

    def test_event_create_post_view_valid_data(self):
        response = self.client.post(reverse("events:event_create"), data=self.data)
        redirect_url = reverse("events:event_detail", kwargs={"event_id": Event.objects.first().id})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect_url)

    def test_event_create_post_view_invalid_data(self):
        data = self.data.copy()
        data["date_end"] = "Not a date"
        response = self.client.post(reverse("events:event_create"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_create.html")
        self.assertIsInstance(response.context["form"], EventForm)

    def test_event_list_with_no_event_created_shows_empty_page(self):
        response = self.client.get(reverse("events:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_list.html")
        self.assertQuerySetEqual(response.context["events"], [])

    def test_event_list_shows_events_in_db(self):
        event = Event.objects.create(**self.data)
        response = self.client.get(reverse("events:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_list.html")
        self.assertQuerySetEqual(response.context["events"], [event])

    def test_event_detail_when_event_id_does_not_exists(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.client.get(reverse("events:event_detail", kwargs={"event_id": 9999}))

    def test_event_detail_when_event_id_does_exists(self):
        event = Event.objects.create(**self.data)
        response = self.client.get(reverse("events:event_detail", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_detail.html")
        self.assertEqual(response.context["event"], event)

    def test_event_update_get_view(self):
        event = Event.objects.create(**self.data)
        response = self.client.get(reverse("events:event_update", kwargs={"event_id": Event.objects.first().id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_update.html")
        self.assertIsInstance(response.context["form"], EventForm)
        self.assertEqual(response.context["event"], event)

    def test_event_update_post_view_valid_data(self):
        event = Event.objects.create(**self.data)
        data = self.data.copy()
        data["date_end"] = date(2025, 12, 31)
        self.assertEqual(event.date_end, self.date_end)

        response = self.client.post(reverse("events:event_update", kwargs={"event_id": Event.objects.first().id}), data=data)
        event.refresh_from_db()
        redirect_url = reverse("events:event_detail", kwargs={"event_id": event.id})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect_url)
        self.assertEqual(event.date_end, data["date_end"])

    def test_event_update_post_view_invalid_data(self):
        event = Event.objects.create(**self.data)
        data = self.data.copy()
        data["date_end"] = "31 de dezembro de 2025"
        self.assertEqual(event.date_end, self.date_end)

        response = self.client.post(reverse("events:event_update", kwargs={"event_id": Event.objects.first().id}), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_update.html")
        self.assertIsInstance(response.context["form"], EventForm)
        self.assertEqual(response.context["event"], event)

    def test_event_update_when_theres_no_event_id(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.client.get(reverse("events:event_update", kwargs={"event_id": 9999}))

    def test_event_delete_get_view(self):
        event = Event.objects.create(**self.data)
        response = self.client.get(reverse("events:event_delete", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_delete.html")
        self.assertEqual(response.context["event"], event)

    def test_event_delete_post_view_valid_data(self):
        event = Event.objects.create(**self.data)

        self.assertEqual(Event.objects.count(), 1)
        response = self.client.post(reverse("events:event_delete", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("events:event_list"))
        self.assertEqual(Event.objects.count(), 0)

    def test_event_delete_when_id_does_not_exists(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.client.get(reverse("events:event_delete", kwargs={"event_id": 9999}))

    def test_event_download_all_certificates(self):
        event = Event.objects.create(**self.data)
        Certificate.objects.create(name="Test Certificate Name",
                                   pronoun="o",
                                   event=event,
                                   hours="02h29",
                                   role="ouvinte")
        Certificate.objects.create(name="Test Certificate Name 2",
                                   pronoun="a",
                                   event=event,
                                   hours="02h29",
                                   role="organizador")
        response = self.client.get(reverse("events:event_download_all", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment; filename=\"{} - {}.zip\"".format(_("Certificates"), event), response["Content-Disposition"])

    def test_event_download_specific_certificate_fails_if_user_doesnt_have_permission_and_downloads_its_own_certificate_of_the_event(self):
        self.user.user_permissions.remove(Permission.objects.get(codename="download_all"))
        self.user.save()
        participant = Participant.objects.create(participant_full_name="Participant_Full_Name",
                                                 participant_username=self.username)

        event = Event.objects.create(**self.data)
        certificate = Certificate.objects.create(name="Test Certificate Name",
                                                 username = participant,
                                                 pronoun="o",
                                                 event=event,
                                                 hours="02h29",
                                                 role="ouvinte")
        Certificate.objects.create(name="Test Certificate Name 2",
                                   pronoun="a",
                                   event=event,
                                   hours="02h29",
                                   role="organizador")
        response = self.client.get(reverse("events:event_download", kwargs={"event_id": event.id, "certificate_id": certificate.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=\"{} - {}.pdf\"".format(_("Certificate"), "Test Certificate Name"), response["Content-Disposition"])

    def test_event_download_specific_certificate_fails_if_user_doesnt_have_permission_and_if_user_doesnt_have_certificate_it_redirects_them(self):
        self.user.user_permissions.remove(Permission.objects.get(codename="download_all"))
        self.user.save()

        event = Event.objects.create(**self.data)
        certificate = Certificate.objects.create(name="Test Certificate Name",
                                                 pronoun="o",
                                                 event=event,
                                                 hours="02h29",
                                                 role="ouvinte")
        Certificate.objects.create(name="Test Certificate Name 2",
                                   pronoun="a",
                                   event=event,
                                   hours="02h29",
                                   role="organizador")
        response = self.client.get(reverse("events:event_download", kwargs={"event_id": event.id, "certificate_id": certificate.id}))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Not Found", status_code=404)

    def test_event_download_a_certificate(self):
        event = Event.objects.create(**self.data)
        certificate = Certificate.objects.create(name="Test Certificate Name",
                                                 pronoun="o",
                                                 event=event,
                                                 hours="02h29",
                                                 role="ouvinte")
        response = self.client.get(reverse("events:event_download", kwargs={"event_id": event.id, "certificate_id": certificate.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=\"{} - {}.pdf\"".format(_("Certificate"), certificate.name), response["Content-Disposition"])

    def test_event_certificate_get_view(self):
        event = Event.objects.create(**self.data)
        response = self.client.get(reverse("events:event_certificate", kwargs={"event_id": event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_certificate_upload.html")
        self.assertEqual(response.context["event"], event)
        self.assertIsInstance(response.context["form"], UploadForm)
        self.assertEqual(response.context["background_link"], settings.LINK_BACKGROUND)
        self.assertEqual(response.context["csv_example"], static('csv_example.csv'))

    def test_event_certificate_post_view_with_valid_data(self):
        event = Event.objects.create(**self.data)
        csv_data = b"name,username,pronoun,hours,role\nTest Name,Test Username,o,02h29,participant"
        valid_csv_file = SimpleUploadedFile("test.csv", csv_data, content_type="text/csv")
        expected_csv_str = pd.read_csv(io.BytesIO(csv_data)).to_html(index=False, justify='center', border=0)
        valid_image_file = SimpleUploadedFile("background.png", b"binarydata", content_type="image/png")

        response = self.client.post(reverse("events:event_certificate", kwargs={"event_id":event.id}), data={"certificate_csv": valid_csv_file, "certificate_background": valid_image_file})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_certificate_confirm.html")
        self.assertEqual(response.context["event"], event)
        self.assertEqual(response.context["table"], expected_csv_str)
        self.assertIsNotNone(response.context["background"])

    def test_event_certificate_post_view_with_missing_columns(self):
        event = Event.objects.create(**self.data)
        csv_data = b"name,username,pronoun,hours\nTest Name,Test Username,o,02h29"
        valid_csv_file = SimpleUploadedFile("test.csv", csv_data, content_type="text/csv")
        valid_image_file = SimpleUploadedFile("background.png", b"binarydata", content_type="image/png")

        response = self.client.post(reverse("events:event_certificate", kwargs={"event_id":event.id}), data={"certificate_csv": valid_csv_file, "certificate_background": valid_image_file})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_certificate_upload.html")
        self.assertEqual(response.context["event"], event)
        self.assertIn(_("One or more required columns are missing. Verify and submit again"), response.context["form"].errors["__all__"])

    def test_event_certificate_post_view_with_invalid_files(self):
        event = Event.objects.create(**self.data)
        csv_data = b"a"
        valid_csv_file = SimpleUploadedFile("test.csv", csv_data, content_type="text/csv")
        valid_image_file = SimpleUploadedFile("background.png", b"binarydata", content_type="image/png")

        response = self.client.post(reverse("events:event_certificate", kwargs={"event_id":event.id}), data={"certificate_csv": valid_csv_file, "certificate_background": valid_image_file})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_certificate_upload.html")
        self.assertEqual(response.context["event"], event)
        self.assertIn(_("One or more required columns are missing. Verify and submit again"), response.context["form"].errors["__all__"])

    def test_event_confirm_certification_with_invalid_event_id(self):
        url = reverse("events:event_confirm_certificate", kwargs={"event_id":99999})
        with self.assertRaises(ObjectDoesNotExist):
            self.client.get(url)

    def test_event_confirm_certification_get_view_redirects_to_event_detail(self):
        event = Event.objects.create(**self.data)
        url = reverse("events:event_confirm_certificate", kwargs={"event_id": event.id})
        response = self.client.get(url)
        redirect_url = reverse("events:event_detail", kwargs={"event_id": event.id})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect_url)

    def test_event_confirm_certification_post_view_with_valid_data(self):
        self.client.login(username=self.username, password=self.password)
        event = Event.objects.create(**self.data)
        data = {"csv_table": "name,username,pronoun,hours,role\nTest Name,Test Username,o,02h29,participant", "background": "background.png"}
        response = self.client.post(reverse("events:event_confirm_certificate", kwargs={"event_id": event.id}), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("events:event_detail", kwargs={"event_id": event.id}))

    def test_event_confirm_certification_post_view_with_missing_data(self):
        self.client.login(username=self.username, password=self.password)
        event = Event.objects.create(**self.data)
        data = {"background": "background.png"}
        response = self.client.post(reverse("events:event_confirm_certificate", kwargs={"event_id": event.id}), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("events:event_certificate", kwargs={"event_id": event.id}))

    def test_event_confirm_certification_post_view_with_invalid_data(self):
        self.client.login(username=self.username, password=self.password)
        event = Event.objects.create(**self.data)
        data = {"csv_table": "name,username,pronoun,hours,role\nTest Name", "background": "background.png"}
        response = self.client.post(reverse("events:event_confirm_certificate", kwargs={"event_id": event.id}), data)
        self.assertRedirects(response, reverse("events:event_certificate", kwargs={"event_id": event.id}))

class FormatDateFilterTest(TestCase):
    def setUp(self):
        self.date_start = date(2024, 1, 1)
        self.date_end_1 = date(2024, 1, 1)
        self.date_end_2 = date(2024, 1, 31)
        self.date_end_3 = date(2024, 12, 31)
        self.date_end_4 = date(2025, 12, 31)
        self.template = Template('{% load custom_tags %}'
                                 '{{ date_start|format_date:date_end }}')
        self.context_1 = Context({'date_start': self.date_start, 'date_end': self.date_end_1})
        self.context_2 = Context({'date_start': self.date_start, 'date_end': self.date_end_2})
        self.context_3 = Context({'date_start': self.date_start, 'date_end': self.date_end_3})
        self.context_4 = Context({'date_start': self.date_start, 'date_end': self.date_end_4})
        self.template_2 = Template('{% load custom_tags %}'
                                   '{{ month|get_month_name }}')
        self.context_5 = Context({'month': self.date_start.month})
        self.context_6 = Context({'month': self.date_end_4.month})

    def test_date_range_single_day(self):
        rendered = self.template.render(self.context_1)
        self.assertEqual(rendered, _("{m_start} {d_start}, {y_start}").format(
            d_start=self.date_start.day,
            m_start=calendar.month_name[self.date_start.month],
            y_start=self.date_start.year))

    def test_date_range_same_month_same_year(self):
        rendered = self.template.render(self.context_2)
        self.assertEqual(rendered, _("{m_start} {d_start} to {d_end}, {y_start}").format(
            d_start=self.date_start.day,
            m_start=calendar.month_name[self.date_start.month],
            y_start=self.date_start.year,
            d_end=self.date_end_2.day))

    def test_date_range_different_month_same_year(self):
        rendered = self.template.render(self.context_3)
        self.assertEqual(rendered, _("{m_start} {d_start} to {m_end} {d_end}, {y_start}").format(
            d_start=self.date_start.day,
            m_start=calendar.month_name[self.date_start.month],
            y_start=self.date_start.year,
            d_end=self.date_end_3.day,
            m_end=calendar.month_name[self.date_end_3.month]))

    def test_date_range_different_year(self):
        rendered = self.template.render(self.context_4)
        self.assertEqual(rendered, _("{m_start} {d_start}, {y_start} to {m_end} {d_end}, {y_end}").format(
            d_start=self.date_start.day,
            m_start=calendar.month_name[self.date_start.month],
            y_start=self.date_start.year,
            d_end=self.date_end_4.day,
            m_end=calendar.month_name[self.date_end_4.month],
            y_end=self.date_end_4.year))

    def test_get_month_name(self):
        rendered = self.template_2.render(self.context_5)
        self.assertEqual(rendered, "janeiro")

        rendered = self.template_2.render(self.context_6)
        self.assertEqual(rendered, "dezembro")