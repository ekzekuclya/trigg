from django.db import models


class TelegramUser(models.Model):
    user_id = models.IntegerField(unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    last_message_time = models.DateTimeField(null=True, blank=True)
    is_operator = models.BooleanField(default=False)

    def __str__(self):
        return self.username if self.username else "None"


class Post(models.Model):
    message_id = models.IntegerField(null=True, blank=True)
    trigger_name = models.CharField(max_length=255)
    photo = models.CharField(max_length=255, null=True, blank=True)


class Button(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    button_name = models.CharField(max_length=255)
    button_click = models.CharField(max_length=2555)
