from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def get_page_context(request, posts):
    paginator = Paginator(posts, settings.ITEMS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    posts = Post.objects.select_related('group', 'author').all()
    context = {
        'page_obj': get_page_context(request, posts),
    }
    template = 'posts/index.html'
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all().select_related('group', 'author')
    context = {
        'group': group,
        'title': group.title,
        'page_obj': get_page_context(request, posts),
    }
    template = 'posts/group_list.html'
    return render(request, template, context)


def profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    posts = user_profile.posts.all().select_related('group', 'author')
    count_posts = posts.count()
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user,
        author=user_profile,
    ).exists()
    context = {
        'user_profile': user_profile,
        'page_obj': get_page_context(request, posts),
        'count_posts': count_posts,
        'following': following
    }
    template = 'posts/profile.html'

    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user_profile = post.author
    count_posts = user_profile.posts.count()
    form = CommentForm()
    comments = post.comments.all().select_related('post', 'author')
    context = {
        'post': post,
        'count_posts': count_posts,
        'user_profile': user_profile,
        'form': form,
        'comments': comments,
    }
    template = 'posts/post_detail.html'
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)

    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})

    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user.username)


@login_required
def post_edit(request, post_id):
    changing_post = get_object_or_404(Post, id=post_id)

    if changing_post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=changing_post
    )

    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post_id = post_id
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = Post.objects.select_related('author').filter(
        author__following__user=request.user)
    context = {
        'page_obj': get_page_context(request, posts)
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follower_user = request.user
    if author != follower_user:
        Follow.objects.get_or_create(user=follower_user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follower_user = request.user
    Follow.objects.filter(user=follower_user, author=author).delete()
    return redirect('posts:profile', username=username)
