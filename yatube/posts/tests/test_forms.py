from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Group, Post

User = get_user_model()


class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

    def test_create_form(self):
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Тестовый текст нового поста UID123',
            'group': self.group.id,
        }

        self.authorised_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        new_post = Post.objects.get(
            text__icontains='UID123',
            author__exact=self.user,
            group__exact=self.group.id
        )

        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.id, form_data['group'])
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
            'text': 'Тестовый текст комментария',
            'author': self.user.username,
            'post': self.post
        }
        response = self.authorised_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        expected_url = reverse('posts:post_detail',
                               kwargs={'post_id': self.post.id})
        self.assertRedirects(response, expected_url,
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             msg_prefix='', fetch_redirect_response=False)

        test_comment = Comment.objects.order_by('-id').first()
        self.assertEqual(test_comment.text, form_data['text'])
        self.assertEqual(test_comment.author.username, form_data['author'])
        self.assertEqual(test_comment.post.id, form_data['post'].id)

        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_redirect_non_auth_create_comment(self):

        comment_count = Comment.objects.count()

        form_data = {
            'text': 'Тестовый текст комментария',
            'author': self.user.username,
            'post': self.post
        }

        response_guest = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        self.assertEqual(response_guest.status_code, HTTPStatus.OK)

        self.assertRedirects(response_guest,
                             reverse('users:login')
                             + '?next='
                             + reverse(
                                 'posts:add_comment',
                                 kwargs={'post_id': self.post.id}))

        self.assertEqual(Comment.objects.count(), comment_count + 0)
