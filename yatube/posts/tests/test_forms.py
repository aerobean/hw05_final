import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cache.clear()

        cls.guest_client = Client()
        cls.user = User.objects.create(username='test_user_forms',)
        cls.authorised_client = Client()
        cls.authorised_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа forms',
            slug='test-slug-forms',
            description='Тестовое описание forms',
        )
        cls.another_group = Group.objects.create(
            title='Другая тестовая группа forms',
            slug='test-slug-another-forms',
            description='Тестовое описание forms',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост forms',
            group=cls.group,
        )
        cls.comments_url = reverse(
            'posts:add_comment', kwargs={'post_id': cls.post.id}
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_form(self):
        posts_count = Post.objects.count()
        single_pix_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        test_image = SimpleUploadedFile(
            name='test_image.gif',
            content=single_pix_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст нового поста UID123',
            'group': self.group.id,
            'image': test_image,
        }

        self.authorised_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        new_post = Post.objects.get(
            # Уникальные данные переданные в форму нового объекта: UID123
            text__icontains='UID123',
            author__exact=self.user,
            group__exact=self.group.id,
            image__exact='posts/test_image.gif',
        )

        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.id, form_data['group'])
        self.assertEqual(
            new_post.image,
            f'{Post._meta.get_field("image").upload_to}{form_data["image"]}'
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_edit_form(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Измененный тестовый текст нового поста UID456',
            'group': self.another_group.id,
        }

        self.authorised_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
        )

        self.post.refresh_from_db()

        self.assertEqual(self.post.text, form_data['text'])
        self.assertEqual(self.post.group.id, form_data['group'])
        self.assertEqual(Post.objects.count(), posts_count)

    def test_create_post_anonimus(self):
        posts_count = Post.objects.count()
        form_data_anonimus = {
            'text': 'Тестовый текст от анонима',
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data_anonimus,
        )
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={reverse("posts:post_create")}',
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                text=form_data_anonimus['text'],
            ).exists()
        )

    def test_create_comment_auth_user_context(self):
        comment_count = Comment.objects.count()

        form_data = {
            'text': 'Тестовый текст комментария UID456',
        }
        response = self.authorised_client.post(
            self.comments_url,
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        expected_url = reverse('posts:post_detail',
                               kwargs={'post_id': self.post.id})
        self.assertRedirects(response, expected_url,
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             msg_prefix='', fetch_redirect_response=False)

        test_comment = Comment.objects.first()
        self.assertEqual(test_comment.text, form_data['text'])
        self.assertEqual(test_comment.author, self.user)
        self.assertEqual(test_comment.post, self.post)
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_redirect_non_auth_create_comment(self):

        comment_count = Comment.objects.count()

        form_data = {
            'text': 'Тестовый текст комментария',
            'author': self.user.username,
            'post': self.post
        }

        response_guest = self.guest_client.post(
            self.comments_url,
            data=form_data,
            follow=True
        )

        self.assertEqual(response_guest.status_code, HTTPStatus.OK)

        self.assertRedirects(
            response_guest,
            f'{reverse("users:login")}?next='
            f'{self.comments_url}',
        )

        self.assertEqual(Comment.objects.count(), comment_count + 0)
