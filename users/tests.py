import os
from django.db import IntegrityError
from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch, Mock

from users.pipeline import get_username
from certificates.models import Certificate
from users.models import User, Participant
from users.forms import UserForm
from users.views import list_media_files, get_used_files, delete_unused_files


class UsersModelTest(TestCase):
    def setUp(self):
        self.username = "Test Username"
        self.full_name = "Test Full Name"

    def test_user_creation(self):
        user = User.objects.create(username=self.username, full_name=self.full_name)
        self.assertEqual(user.username, self.username)
        self.assertEqual(user.full_name, self.full_name)

    def test_unique_username(self):
        User.objects.create(username=self.username, full_name=self.full_name)
        with self.assertRaises(IntegrityError):
            User.objects.create(username=self.username, full_name='Test Full Name 2')

    def test_username_max_length(self):
        long_username = 'a' * 151
        with self.assertRaises(ValidationError):
            user = User(username=long_username)
            user.full_clean()

    def test_full_name_max_length(self):
        long_full_name = 'a' * 301
        with self.assertRaises(ValidationError):
            user = User(username=self.username, full_name=long_full_name)
            user.full_clean()

    def test_str_method(self):
        user = User.objects.create(username=self.username, full_name=self.full_name)
        self.assertEqual(str(user), self.username)


class ParticipantModelTest(TestCase):
    def setUp(self):
        self.username = "Test Username"
        self.full_name = "Test Full Name"

    def test_participant_creation(self):
        participant = Participant.objects.create(
            participant_username=self.username,
            participant_full_name=self.full_name,
            number_of_certificates=5
        )
        self.assertEqual(participant.participant_username, self.username)
        self.assertEqual(participant.participant_full_name, self.full_name)
        self.assertEqual(participant.number_of_certificates, 5)
        self.assertIsNone(participant.enrolled_at)
        self.assertIsNotNone(participant.created_at)
        self.assertIsNotNone(participant.modified_at)

    def test_participant_username_max_length(self):
        long_username = 'a' * 151
        with self.assertRaises(ValidationError):
            participant = Participant(participant_username=long_username, participant_full_name=self.full_name)
            participant.full_clean()  # This will trigger validation

    def test_participant_full_name_max_length(self):
        long_full_name = 'a' * 301
        with self.assertRaises(ValidationError):
            participant = Participant(participant_username=self.username, participant_full_name=long_full_name)
            participant.full_clean()

    def test_number_of_certificates_default(self):
        participant = Participant.objects.create(participant_username=self.username)
        self.assertEqual(participant.number_of_certificates, 0)

    def test_enrolled_at_nullable(self):
        participant = Participant.objects.create(participant_username=self.username)
        self.assertIsNone(participant.enrolled_at)

    def test_created_by_nullable(self):
        participant = Participant.objects.create(participant_username=self.username)
        self.assertIsNone(participant.created_by)

    def test_modified_by_nullable(self):
        participant = Participant.objects.create(participant_username=self.username)
        self.assertIsNone(participant.modified_by)

    def test_str_method(self):
        participant = Participant.objects.create(participant_username=self.username,
                                                 participant_full_name=self.full_name)
        self.assertEqual(str(participant), self.username)

    def test_str_method_without_participant_username(self):
        participant = Participant.objects.create(participant_full_name=self.full_name)
        self.assertEqual(str(participant), "")

    def test_created_by_foreign_key(self):
        creator = User.objects.create(username='Test User', password='Password')
        participant = Participant.objects.create(participant_username=self.username, created_by=creator)
        self.assertEqual(participant.created_by, creator)

    def test_modified_by_foreign_key(self):
        modifier = User.objects.create(username='Test User', password='Password')
        participant = Participant.objects.create(participant_username=self.username, modified_by=modifier)
        self.assertEqual(participant.modified_by, modifier)


class UserFormTest(TestCase):
    def setUp(self):
        self.username = "Test Username"

    def test_user_form_valid(self):
        data = {'username': self.username}
        form = UserForm(data)
        self.assertTrue(form.is_valid())

    def test_user_form_username_max_length(self):
        data = {'username': 'a' * 151}
        form = UserForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_form_unique_username(self):
        User.objects.create(username=self.username)

        data = {'username': self.username}
        form = UserForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_user_form_cleaned_data(self):
        data = {'username': self.username}
        form = UserForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['username'], self.username)


class UserViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_login(self.user)

    def test_index_view(self):
        response = self.client.get(reverse('users:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/index.html')

    def test_login_oauth_view(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('social:begin', kwargs={'backend': 'mediawiki'})
        self.assertEqual(response.url, expected_url)

    def test_logout_oauth_view(self):
        response = self.client.get(reverse('users:logout'))
        self.assertRedirects(response, reverse('users:index'))
        self.assertFalse('_auth_user_id' in self.client.session)


class TestListMediaFiles(TestCase):
    def setUp(self):
        self.test_media_root = "/test/media/root"
        self.settings_patcher = patch('django.conf.settings')
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.MEDIA_ROOT = self.test_media_root

    def tearDown(self):
        self.settings_patcher.stop()

    @patch('os.walk')
    @patch('django.conf.settings.MEDIA_ROOT', '/test/media/root')
    def test_empty_directory(self, mock_walk):
        mock_walk.return_value = [(self.test_media_root, [], [])]

        result = list_media_files()

        self.assertEqual(result, [])
        mock_walk.assert_called_once()

    @patch('os.walk')
    def test_single_file(self, mock_walk):
        mock_walk.return_value = [(self.test_media_root, [], ['test.jpg'])]

        result = list_media_files()
        relative_results = []
        for path in result:
            rel_path = os.path.relpath(path, self.test_media_root)
            rel_path = rel_path.replace(os.sep, '/')
            relative_results.append(rel_path)

        self.assertEqual(relative_results, ['test.jpg'])

    @patch('os.walk')
    def test_nested_directories(self, mock_walk):
        mock_walk.return_value = [(self.test_media_root, ['dir1'], ['root.txt']),
                                  (os.path.join(self.test_media_root, 'dir1'), [], ['nested.jpg'])]

        result = list_media_files()

        relative_results = []
        for path in result:
            rel_path = os.path.relpath(path, self.test_media_root)
            rel_path = rel_path.replace(os.sep, '/')
            relative_results.append(rel_path)

        expected = ['root.txt', 'dir1/nested.jpg']
        self.assertEqual(relative_results, expected)

    @patch('os.walk')
    def test_multiple_files_and_directories(self, mock_walk):
        mock_walk.return_value = [(self.test_media_root, ['dir1', 'dir2'], ['root1.txt', 'root2.jpg']),
                                  (os.path.join(self.test_media_root, 'dir1'), [], ['file1.pdf']),
                                  (os.path.join(self.test_media_root, 'dir2'), ['subdir'], ['file2.doc']),
                                  (os.path.join(self.test_media_root, 'dir2', 'subdir'), [], ['deep.png'])]

        result = list_media_files()

        relative_results = []
        for path in result:
            rel_path = os.path.relpath(path, self.test_media_root)
            rel_path = rel_path.replace(os.sep, '/')
            relative_results.append(rel_path)

        expected = ['root1.txt', 'root2.jpg', 'dir1/file1.pdf', 'dir2/file2.doc', 'dir2/subdir/deep.png']
        self.assertEqual(relative_results, expected)

    @patch('os.walk')
    def test_windows_path_conversion(self, mock_walk):
        mock_walk.return_value = [(self.test_media_root, ['dir1'], []),
                                  (os.path.join(self.test_media_root, 'dir1'), [], ['file.txt'])]

        # Simulate Windows-style paths
        with patch('os.path.join', return_value=self.test_media_root + "\\dir1\\file.txt"):
            with patch('os.path.relpath', return_value="dir1\\file.txt"):
                result = list_media_files()

                self.assertEqual(result, ['dir1/file.txt'])

    def test_media_root_not_found(self):
        with patch('os.walk', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                list_media_files()


class GetUsedFilesTests(TestCase):
    def setUp(self):
        Certificate.objects.create(background='backgrounds/file1.jpg')
        Certificate.objects.create(background='backgrounds/file2.png')
        Certificate.objects.create(background='file3.pdf')
        Certificate.objects.create(background=None)
        Certificate.objects.create(background='')

    def test_get_used_files_returns_set(self):
        result = get_used_files()
        self.assertIsInstance(result, set)

    def test_get_used_files_returns_only_basenames(self):
        result = get_used_files()
        expected = {'file1.jpg', 'file2.png', 'file3.pdf'}
        self.assertEqual(result, expected)

    def test_get_used_files_handles_empty_database(self):
        Certificate.objects.all().delete()
        result = get_used_files()
        self.assertEqual(result, set())

    def test_get_used_files_filters_none_and_empty(self):
        result = get_used_files()
        self.assertNotIn('', result)
        self.assertNotIn(None, result)

    def test_get_used_files_handles_duplicates(self):
        Certificate.objects.create(background='backgrounds/file1.jpg')
        result = get_used_files()
        self.assertEqual(len([f for f in result if f == 'file1.jpg']), 1)

    @patch('os.path.basename')
    def test_get_used_files_calls_basename(self, mock_basename):
        mock_basename.side_effect = lambda x: f"base_{x}"
        get_used_files()
        self.assertEqual(mock_basename.call_count, 3)

    def test_get_used_files_with_special_characters(self):
        Certificate.objects.create(background='backgrounds/file with spaces.jpg')
        Certificate.objects.create(background='backgrounds/file_with_!@#$.jpg')
        result = get_used_files()
        self.assertIn('file with spaces.jpg', result)
        self.assertIn('file_with_!@#$.jpg', result)

    def test_get_used_files_with_same_filename_different_paths(self):
        Certificate.objects.create(background='path1/common.jpg')
        Certificate.objects.create(background='path2/common.jpg')
        result = get_used_files()
        self.assertEqual(len([f for f in result if f == 'common.jpg']), 1)

    def test_get_used_files_case_sensitivity(self):
        Certificate.objects.create(background='backgrounds/File1.jpg')
        Certificate.objects.create(background='backgrounds/file1.JPG')
        result = get_used_files()
        self.assertIn('File1.jpg', result)
        self.assertIn('file1.JPG', result)


class TestDeleteUnusedFiles(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get(reverse("users:clean_files"))

        self.test_media_root = os.path.join(settings.BASE_DIR, 'test_media')
        self.old_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self.test_media_root

        if not os.path.exists(self.test_media_root):
            os.makedirs(self.test_media_root)

    def tearDown(self):
        if os.path.exists(self.test_media_root):
            for root, dirs, files in os.walk(self.test_media_root, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.test_media_root)

        settings.MEDIA_ROOT = self.old_media_root

    def create_test_file(self, filename):
        file_path = os.path.join(self.test_media_root, filename)
        with open(file_path, 'w') as f:
            f.write('test content')
        return filename

    @patch('users.views.list_media_files')
    @patch('users.views.get_used_files')
    def test_successful_deletion_of_unused_files(self, mock_get_used, mock_list_media):
        test_files = ['test1.txt', 'test2.txt', 'test3.txt']
        for filename in test_files:
            self.create_test_file(filename)

        mock_list_media.return_value = test_files
        mock_get_used.return_value = {'test1.txt'}  # Only test1.txt is used

        response = delete_unused_files(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Deleted all unused files.")

        self.assertTrue(os.path.exists(os.path.join(self.test_media_root, 'test1.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, 'test2.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, 'test3.txt')))

    @patch('users.views.list_media_files')
    @patch('users.views.get_used_files')
    def test_no_files_to_delete(self, mock_get_used, mock_list_media):
        test_files = ['test1.txt', 'test2.txt']
        for filename in test_files:
            self.create_test_file(filename)

        mock_list_media.return_value = test_files
        mock_get_used.return_value = set(test_files)

        response = delete_unused_files(self.request)

        self.assertEqual(response.status_code, 200)
        for filename in test_files:
            self.assertTrue(os.path.exists(os.path.join(self.test_media_root, filename)))

    @patch('users.views.list_media_files')
    @patch('users.views.get_used_files')
    def test_handle_nonexistent_files(self, mock_get_used, mock_list_media):
        self.create_test_file('existing.txt')

        mock_list_media.return_value = ['existing.txt', 'nonexistent.txt']
        mock_get_used.return_value = set()

        response = delete_unused_files(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, 'existing.txt')))

    @patch('users.views.list_media_files')
    @patch('users.views.get_used_files')
    def test_empty_media_directory(self, mock_get_used, mock_list_media):
        mock_list_media.return_value = []
        mock_get_used.return_value = set()

        response = delete_unused_files(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Deleted all unused files.")

    @patch('users.views.list_media_files')
    @patch('users.views.get_used_files')
    def test_media_root_handling(self, mock_get_used, mock_list_media):
        test_file = 'test_file.txt'
        self.create_test_file(test_file)

        mock_list_media.return_value = [test_file]
        mock_get_used.return_value = set()

        response = delete_unused_files(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, test_file)))

class TestPipeline(TestCase):
    def test_get_username_with_existing_user(self):
        mock_user = Mock()
        mock_user.username = "existing_user"
        mock_strategy = Mock()
        mock_details = {"username": "details_username"}  # This shouldn't be used

        result = get_username(
            strategy=mock_strategy,
            details=mock_details,
            user=mock_user
        )

        self.assertEqual(result, {"username": "existing_user"})

    def test_get_username_without_user(self):
        mock_strategy = Mock()
        mock_details = {"username": "new_user"}

        result = get_username(
            strategy=mock_strategy,
            details=mock_details,
            user=None
        )

        self.assertEqual(result, {"username": "new_user"})

    def test_get_username_without_user_missing_username(self):
        mock_strategy = Mock()
        mock_details = {}  # Missing username

        with self.assertRaises(KeyError):
            get_username(
                strategy=mock_strategy,
                details=mock_details,
                user=None
            )