from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CommentForm, CustomUserCreationForm, PostForm, UserForm
from .models import Category, Comment, Post

User = get_user_model()

PAGINATE_BY = 10


class IndexView(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = PAGINATE_BY
    context_object_name = 'page_obj'

    def get_queryset(self):
        return (
            Post.objects.filter(
                is_published=True,
                category__is_published=True,
                pub_date__lte=timezone.now(),
            )
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )


class CategoryPostsView(ListView):
    template_name = 'blog/category.html'
    paginate_by = PAGINATE_BY
    context_object_name = 'page_obj'

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, slug=self.kwargs['slug'], is_published=True
        )
        return (
            Post.objects.filter(
                category=self.category,
                is_published=True,
                pub_date__lte=timezone.now(),
            )
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        qs = Post.objects.select_related('author', 'category', 'location')
        if self.request.user.is_authenticated:
            return qs.filter(
                models.Q(
                    is_published=True,
                    category__is_published=True,
                    pub_date__lte=timezone.now(),
                )
                | models.Q(author=self.request.user)
            )
        return qs.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class ProfileView(ListView):
    template_name = 'blog/profile.html'
    paginate_by = PAGINATE_BY
    context_object_name = 'page_obj'

    def get_queryset(self):
        self.profile = get_object_or_404(User, username=self.kwargs['username'])
        qs = Post.objects.filter(author=self.profile).annotate(
            comment_count=Count('comments')
        )
        if self.request.user != self.profile:
            qs = qs.filter(is_published=True, category__is_published=True)
        return qs.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile
        return context


class CreatePostView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class EditPostView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        post = self.get_object()
        return post.author == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect(
                'blog:post_detail', post_id=self.kwargs['post_id']
            )
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.pk})


class DeletePostView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def test_func(self):
        return self.get_object().author == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context

    def get_success_url(self):
        return reverse(
            'blog:profile', kwargs={'username': self.request.user.username}
        )


class AddCommentView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/detail.html'

    def form_valid(self, form):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        form.instance.post = post
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class EditCommentView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        return self.get_object().author == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment'] = self.object
        return context

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class DeleteCommentView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def test_func(self):
        return self.get_object().author == self.request.user

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class EditProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})


class RegistrationView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = '/auth/login/'