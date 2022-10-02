from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='test_user',
            email='test@test.test',
            password='test_password',
        )
        cls.another_user = User.objects.create(username='another_test_user')

        cls.guest_client = Client()
        cls.authorised_client = Client()
        cls.authorised_client.force_login(cls.user)
        cls.authorised_another_client = Client()
        cls.authorised_another_client.force_login(cls.another_user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def test_unauthorised(self):
        url_status_code = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            f'/profile/{self.user.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND
        }

        for url, status in url_status_code.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status)

    def test_authorised(self):
        response = self.authorised_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author(self):
        response = self.authorised_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_non_author(self):
        response = self.authorised_another_client.get(
            f'/posts/{self.post.id}/edit/'
        )
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id})
        )

    def test_post_edit_redirect_anonymus(self):
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/'
        )
        self.assertRedirects(
            response, f'{reverse("users:login")}?next='
            f'{reverse("posts:post_edit", kwargs={"post_id": self.post.id})}'
        )

    def test_post_create_redirect_anonymos(self):
        response = self.guest_client.get('/create/')
        self.assertRedirects(
            response, f'{reverse("users:login")}?next='
            f'{reverse("posts:post_create")}'
        )

    def test_correct_templates_used(self):
        test_urls = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html'
        }

        for url, template in test_urls.items():
            with self.subTest(url=url):
                response = self.authorised_client.get(url)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)
