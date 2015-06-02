from django.db import models


class Plants(models.Model):
    name = models.CharField(max_length=120)


class Trees(models.Model):
    name = models.CharField(max_length=120)
    plant = models.ForeignKey(Plants)
