import settings

from django_webtest import WebTest
from core         import models
from tasks.models import Task
from django.test.client import Client
from django.contrib.auth.models import User

from django_date_extensions.fields import ApproximateDate
from django.contrib.contenttypes.models import ContentType, ContentTypeManager

import pprint
import mz_comments

class CommentsCase(WebTest):
    def setUp(self):
        self.person, created = models.Person.objects.get_or_create(
            first_name = 'Test',
            last_name  = 'Person',
            slug       = 'test-person',
        )
        
        self.test_user = User.objects.create_user(
            username = 'test-admin',
            email    = 'test-admin@example.com',
            password = 'secret',
        )

    def test_leaving_comment(self):
        # go to the person and check that there are no comments
        person = self.person
        person_url = person.get_absolute_url()
        app = self.app
        response = app.get( person_url )
        self.assertEqual(response.status_int, 200)                
        
        # check that anon can't leave comments
        self.assertTemplateNotUsed( response, 'comments/form.html' )
        self.assertContains( response, "login to leave a comment" )
        
        # check that there is now a comment form
        response = app.get( person_url, user=self.test_user )
        self.assertTemplateUsed( response, 'comments/form.html' )
        
        # leave a comment
        form = response.form
        form['title']   = 'Test Title'
        form['comment'] = 'Test comment'
        form_response = form.submit()
        self.assertEqual(response.context['user'].username, 'test-admin')

        # check that the comment is correct and pending review
        comment = mz_comments.models.CommentWithTitle.objects.filter(
            content_type = ContentTypeManager().get_for_model(self.person),
            object_pk    = self.person.id,
        )[0]
        self.assertEqual( comment.title, 'Test Title' )
        self.assertEqual( comment.comment, 'Test comment' )
        self.assertEqual( comment.name, 'test-admin' )
        self.assertEqual( comment.is_public, False )
        self.assertEqual( comment.is_removed, False )
        
        # check it is not visible on site
        res = app.get( person_url )
        self.assertNotContains( res, comment.title )
                
        # approve the comment
        comment.is_public = True
        comment.save()
        
        # check that it is shown on site
        self.assertContains( app.get( person_url ), comment.title )
        
        # flag the comment
        comment.is_removed = True
        comment.save()
        self.assertNotContains( app.get( person_url ), comment.title )
        
        # delete the comment
        comment.delete()
        # check that comment not shown
        res = app.get( person_url )
        self.assertNotContains( res, comment.title )
        self.assertNotContains( res, 'comment removed' )
        