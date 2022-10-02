import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.guest_client = Client()
        cls.user = User.objects.create(username='test_user_views',)
        cls.authorised_client = Client()
        cls.authorised_client.force_login(cls.user)
        cls.another_user = User.objects.create(
            username='test_another_user_views',)
        cls.another_authorised_client = Client()
        cls.another_authorised_client.force_login(cls.another_user)
        cls.user_follow = User.objects.create(
            username='author_test_follow')
        cls.authorised_client_follow = Client()
        cls.authorised_client_follow.force_login(cls.user_follow)

        single_pix_png = (
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVE'
            b'UAAACnej3aAAAAAXRSTlMAQObYZgAAAApJREFUCNdjYAAAAAIAAeIh'
            b'vDMAAAAASUVORK5CYII='
        )
        test_image = SimpleUploadedFile(
            name='test_image.png',
            content=single_pix_png,
            content_type='image/png'
        )

        cls.group = Group.objects.create(
            title='Тестовая группа views',
            slug='test-slug-views',
            description='Тестовое описание views',
        )
        cls.another_group = Group.objects.create(
            title='Тестовая группа без поста views',
            slug='test-slug-no-post-views',
            description='Тестовое описание группы без поста views',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост views',
            group=cls.group,
            image=test_image,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def _check_post_details(self, response, object_type):
        if object_type == 'page':
            object_for_tests = response.context['post_list'][0]
        else:
            object_for_tests = response.context['post']
        post_id_0 = object_for_tests.id
        post_text_0 = object_for_tests.text
        post_author_0 = object_for_tests.author.username
        post_group_0 = object_for_tests.group.slug
        post_image_0 = object_for_tests.image
        self.assertEqual(post_id_0, self.post.id)
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_author_0, self.post.author.username)
        self.assertEqual(post_group_0, self.post.group.slug)
        self.assertEqual(post_image_0, self.post.image)

    def test_posts_post_on_index_view_context(self):
        response = self.authorised_client.get(reverse('posts:index'))
        object_type = 'page'
        self._check_post_details(response, object_type)

    def test_posts_post_on_group_list_view_context(self):
        response = self.authorised_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        object_type = 'page'
        self._check_post_details(response, object_type)
        self.assertEqual(response.context['group'], self.group)

    def test_posts_post_on_profile_page_view_context(self):
        response = self.authorised_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author})
        )
        object_type = 'page'
        self._check_post_details(response, object_type)
        self.assertEqual(response.context['user_profile'], self.user)

    def test_post_detail_view_context(self):
        response = self.authorised_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        object_type = 'post'
        self._check_post_details(response, object_type)

    def test_post_not_in_another_group(self):
        response = self.authorised_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.another_group.slug})
        )
        post_not_in_group = response.context['post_list']
        self.assertNotIn(self.post, post_not_in_group)

    def test_post_not_in_another_user_profile(self):
        response = self.another_authorised_client.get(
            reverse('posts:profile', kwargs={'username': self.another_user})
        )
        post_not_in_another_user = response.context['post_list']
        self.assertNotIn(self.post, post_not_in_another_user)

    def test_create_view_context(self):
        response = self.authorised_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), None)

    def test_edit_post_view_context(self):
        response = self.authorised_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), True)

    def test_cache_index_page(self):

        form_data = {
            'text': 'Тестовый пост для проверки кэша',
            'author': self.user.username,
            'group': self.group.id,
        }

        response = self.another_authorised_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        response_before_cache = self.authorised_client.get(
            reverse('posts:index')
        )
        content_before_cache = response_before_cache.content

        Post.objects.order_by('-id').first().delete()

        self.assertFalse(Post.objects.filter(
            text=form_data['text'])
        )

        response_from_cache = self.authorised_client.get(
            reverse('posts:index')
        )
        content_from_cashe = response_from_cache.content

        self.assertEqual(content_before_cache, content_from_cashe)

        cache.clear()

        response_after_cache = self.authorised_client.get(
            reverse('posts:index')
        )
        content_after_cache = response_after_cache.content
        self.assertNotEqual(content_after_cache, content_before_cache)

    def test_following_author(self):

        author = self.user
        follower = self.another_user
        followers_count_before = Follow.objects.all().count()
        response = self.another_authorised_client.post(reverse(
            'posts:profile_follow', kwargs={'username': self.post.author}))

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        followers_count_after = Follow.objects.all().count()
        self.assertEqual(followers_count_after, followers_count_before + 1)

        follower_to_check = Follow.objects.get(author=author, user=follower)
        self.assertEqual(follower_to_check.author, author)
        self.assertEqual(follower_to_check.user, follower)

    def test_unfollowing_author(self):

        author = self.user
        follower = self.another_user
        Follow.objects.create(user=follower, author=author)
        followers_count_before = Follow.objects.all().count()
        response = self.another_authorised_client.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.post.author}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        followers_count_after = Follow.objects.all().count()
        self.assertEqual(followers_count_after, followers_count_before - 1)
        self.assertFalse(Follow.objects.filter(author=author, user=follower))

    def test_follower_get_updates_from_author(self):

        post_test_follow = Post.objects.create(
            text='Тестовый пост для тестирования ленты подписок',
            author=self.user_follow,
            group=self.group,
        )
        author = self.user_follow
        follower = self.another_user
        Follow.objects.create(user=follower, author=author)
        response_follower = self.another_authorised_client.get(
            reverse('posts:follow_index')
        )
        follow_obj = response_follower.context['post_list'][0]
        post_id = follow_obj.pk
        post_text = follow_obj.text

        self.assertEqual(post_id, post_test_follow.id)
        self.assertEqual(post_text, post_test_follow.text)
        self.assertEqual(len(response_follower.context['post_list']), 1)

    def test_not_follower_do_not_get_updates_from_author(self):

        Post.objects.create(
            text='Тестовый пост для тестирования ленты подписок',
            author=self.user_follow,
            group=self.group,
        )
        author = self.user_follow
        follower = self.another_user
        Follow.objects.create(user=follower, author=author)
        response_non_follower = self.authorised_client.get(
            reverse('posts:follow_index')
        )

        self.assertEqual(len(response_non_follower.context['post_list']), 0)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create(username='test_user_views_page',)
        cls.authorised_client = Client()
        cls.authorised_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа views',
            slug='test-slug-views-page',
            description='Тестовое описание views',
        )

        cls.posts_quantity = 13
        cls.posts_per_page = 10
        cls.posts_obj = []

        for pk in range(cls.posts_quantity):
            cls.posts_obj.append(Post(
                                 pk=pk,
                                 text=f'Тестовый пост № {pk}',
                                 author=cls.user,
                                 group=cls.group,))

        Post.objects.bulk_create(cls.posts_obj, cls.posts_quantity)

    def test_first_page_contains_ten_posts(self):
        views = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        )
        for view in views:
            with self.subTest(view=view):
                response = self.authorised_client.get(view)
                self.assertEqual(
                    len(response.context['post_list']), self.posts_per_page
                )

    def test_second_page_contains_left_posts(self):
        group = self.group.slug
        user = self.user.username
        views = (
            f'{reverse("posts:index")}?page=2',
            f'{reverse("posts:group_list", kwargs={"slug": group})}'
            f'?page=2',
            f'{reverse("posts:profile", kwargs={"username": user})}'
            f'?page=2',
        )
        for view in views:
            with self.subTest(view=view):
                response = self.authorised_client.get(view)
                self.assertEqual(
                    len(response.context['post_list']),
                    int(self.posts_quantity - self.posts_per_page)
                )
