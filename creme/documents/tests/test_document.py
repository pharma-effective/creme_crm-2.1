# -*- coding: utf-8 -*-

try:
    import filecmp
    from functools import partial
    from json import dumps as json_dump
    from os.path import join, exists

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _
    from django.test import override_settings

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui.field_printers import field_printers_registry
    from creme.creme_core.models import CremeEntity, RelationType, HeaderFilter, SetCredentials
    from creme.creme_core.tests.fake_models import FakeOrganisation as Organisation

    from creme.persons.tests.base import skipIfCustomContact
    from creme.persons import get_contact_model

    from .base import (_DocumentsTestCase, skipIfCustomDocument,
            skipIfCustomFolder, Folder, Document)
    from ..models import FolderCategory, DocumentCategory
    from ..constants import REL_SUB_RELATED_2_DOC
    from ..utils import get_csv_folder_or_create
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentTestCase(_DocumentsTestCase):
    def _buid_addrelated_url(self, entity):
        return reverse('documents__create_related_document', args=(entity.id,))

    def test_populate(self):
        self.get_object_or_fail(RelationType, pk=REL_SUB_RELATED_2_DOC)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Document)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Folder)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())
        self.assertTrue(DocumentCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertGET200('/documents/')

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'pdf'))
    def test_createview01(self):
        self.login()

        self.assertFalse(Document.objects.exists())

        url = self.ADD_DOC_URL
        self.assertGET200(url)

        # ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
        # self.assertTrue(ALLOWED_EXTENSIONS)
        # ext = ALLOWED_EXTENSIONS[0]
        ext = settings.ALLOWED_EXTENSIONS[0]

        title = 'Test doc'
        description = 'Test description'
        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj, file_name = self._build_filedata(content, suffix='.%s' % ext)
        folder = Folder.objects.all()[0]
        response = self.client.post(self.ADD_DOC_URL, follow=True,
                                    data={'user':     self.user.pk,
                                          'title':    title,
                                          'filedata': file_obj,
                                          'folder':   folder.id,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        mime_type = doc.mime_type
        self.assertIsNotNone(mime_type)

        self.assertRedirects(response, doc.get_absolute_url())

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s' % file_name, filedata.name)
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        # Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview02(self):
        "Forbidden extension"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='.%s' % ext)
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        # Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview03(self):
        "Double extension (bugfix)"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='.old.%s' % ext)
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        # Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview04(self):
        "No extension"
        self.login()

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='')
        doc = self._create_doc(title, file_obj)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        # Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual('txt', response['Content-Type']) # 'text/plain' ??
        self.assertEqual('attachment; filename=%s.txt' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview05(self):
        "No title"
        user = self.login()

        ext = settings.ALLOWED_EXTENSIONS[0]
        file_obj, file_name = self._build_filedata('Content', suffix='.%s' % ext)

        folder = Folder.objects.create(user=user, title='test_createview05')
        response = self.client.post(self.ADD_DOC_URL, follow=True,
                                    data={'user':     user.pk,
                                          # 'title':    '',
                                          'filedata': file_obj,
                                          'folder':   folder.id,
                                         }
                                   )

        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, folder=folder)
        self.assertEqual('upload/documents/%s' % file_name, doc.filedata.name)
        self.assertEqual(file_name, doc.title)

    def test_download_error(self):
        self.login()
        self.assertGET404('/download_file/%s' % 'tmpLz48vy.txt')

    def test_editview(self):
        user = self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = 'Yes I am the content (DocumentTestCase.test_editview)'
        doc = self._create_doc(title, self._build_filedata(content)[0], description=description)

        url = doc.get_edit_absolute_url()
        self.assertGET200(url)

        title       = title.upper()
        description = description.upper()
        # content     = content.upper() TODO: use ?
        folder      = Folder.objects.create(title=u'Test folder', parent_folder=None,
                                            category=FolderCategory.objects.all()[0],
                                            user=user,
                                           )

        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        doc = self.refresh(doc)
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        self.assertRedirects(response, doc.get_absolute_url())

    def test_add_related_document01(self):
        user = self.login()

        # folders = Folder.objects.all()
        folders = Folder.objects.order_by('id')
        # self.assertEqual(1, len(folders))
        self.assertEqual(2, len(folders))
        root_folder = folders[0]

        entity = CremeEntity.objects.create(user=user)

        url = self._buid_addrelated_url(entity)
        self.assertGET200(url)

        def post(title):
            response = self.client.post(url, follow=True,
                                        data={'user':         user.pk,
                                              'title':        title,
                                              'description':  'Test description',
                                              'filedata':     self._build_filedata('Yes I am the content '
                                                                                   '(DocumentTestCase.test_add_related_document01)'
                                                                                  )[0],
                                             }
                                    )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        doc1 = post('Related doc')
        self.assertRelationCount(1, entity, REL_SUB_RELATED_2_DOC, doc1)

        entity_folder = doc1.folder
        self.assertIsNotNone(entity_folder)
        self.assertEqual(u'%s_%s' % (entity.id, unicode(entity)), entity_folder.title)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(unicode(CremeEntity._meta.verbose_name), ct_folder.title)
        self.assertEqual(root_folder, ct_folder.parent_folder)

        doc2 = post('Related doc #2')
        entity_folder2 = doc2.folder
        self.assertEqual(entity_folder, entity_folder2)
        self.assertEqual(ct_folder,     entity_folder2.parent_folder)

    def test_add_related_document02(self):
        "Creation credentials"
        self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'])

        entity = CremeEntity.objects.create(user=self.user)
        self.assertGET403(self._buid_addrelated_url(entity))

    def test_add_related_document03(self):
        "Link credentials"
        user = self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'],
                          creatable_models=[Document]
                         )

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_OWN,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not EntityCredentials.LINK
                 )

        orga = Organisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._buid_addrelated_url(orga)
        self.assertGET403(url)

        get_ct = ContentType.objects.get_for_model
        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Organisation))
        self.assertGET403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Document))
        self.assertGET200(url)

        response = self.assertPOST200(url, follow=True,
                                      data={'user':         self.other_user.pk,
                                            'title':        'Title',
                                            'description':  'Test description',
                                            'filedata':     self._build_filedata('Yes I am the content '
                                                                                 '(DocumentTestCase.test_add_related_document03)'
                                                                                )[0],
                                           }
                                     )
        self.assertFormError(response, 'form', 'user',
                             _(u'You are not allowed to link with the «%s» of this user.') % _(u'Documents')
                            )

    def test_add_related_document04(self):
        "View credentials"
        user = self.login(is_superuser=False, allowed_apps=['documents', 'creme_core'],
                          creatable_models=[Document],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,  # Not EntityCredentials.VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertTrue(user.has_perm_to_link(orga))
        self.assertFalse(user.has_perm_to_view(orga))
        self.assertGET403(self._buid_addrelated_url(orga))

    def test_add_related_document05(self):
        "The Folder containing all the Documents related to the entity has a too long name."
        user = self.login()

        MAX_LEN = 100
        self.assertEqual(MAX_LEN, Folder._meta.get_field('title').max_length)

        with self.assertNoException():
            entity = Organisation.objects.create(user=user, name='A' * MAX_LEN)

        self.assertEqual(100, len(unicode(entity)))

        title    = 'Related doc'
        response = self.client.post(self._buid_addrelated_url(entity),
                                    follow=True,
                                    data={'user':        user.pk,
                                          'title':       title,
                                          'description': 'Test description',
                                          'filedata':    self._build_filedata('Yes I am the content '
                                                                              '(DocumentTestCase.test_add_related_document05)'
                                                                             )[0],
                                         }
                                   )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)
        entity_folder = doc.folder
        self.assertIsNotNone(entity_folder)

        title = entity_folder.title
        self.assertEqual(100, len(title))
        self.assertTrue(title.startswith(u'%s_AAAAAAA' % entity.id))
        self.assertTrue(title.endswith(u'…'))

    def test_add_related_document06(self):
        "Collision with Folder titles"
        user = self.login()
        entity = CremeEntity.objects.create(user=user)

        creme_folder = self.get_object_or_fail(Folder, title='Creme')

        # NB : collision with folders created by the view
        create_folder = partial(Folder.objects.create, user=user)
        my_ct_folder = create_folder(title=unicode(entity.entity_type))
        my_entity_folder = create_folder(title=u'%s_%s' % (entity.id, entity))

        title = 'Related doc'
        response = self.client.post(self._buid_addrelated_url(entity), follow=True,
                                    data={'user':         user.pk,
                                          'title':        title,
                                          'description':  'Test description',
                                          'filedata':     self._build_filedata('Yes I am the content '
                                                                               '(DocumentTestCase.test_add_related_document06)'
                                                                              )[0],
                                         }
                                )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)

        entity_folder = doc.folder
        self.assertEqual(my_entity_folder.title, entity_folder.title)
        self.assertNotEqual(my_entity_folder, entity_folder)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(my_ct_folder.title, ct_folder.title)
        self.assertNotEqual(my_ct_folder, ct_folder)

        self.assertEqual(creme_folder, ct_folder.parent_folder)

    def test_listview(self):
        self.login()

        create_doc = self._create_doc
        doc1 = create_doc('Test doc #1')
        doc2 = create_doc('Test doc #2')

        response = self.assertGET200(Document.get_lv_absolute_url())

        with self.assertNoException():
            docs = response.context['entities'].object_list

        self.assertIn(doc1, docs)
        self.assertIn(doc2, docs)

    def test_delete_category(self):
        "Set to null"
        user = self.login()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=user, title='One piece', category=cat)

        self.assertPOST200('/creme_config/documents/category/delete', data={'id': cat.pk})
        self.assertDoesNotExist(cat)

        folder = self.get_object_or_fail(Folder, pk=folder.pk)
        self.assertIsNone(folder.category)

    @skipIfCustomContact
    def test_field_printers01(self):
        "Field printer with FK on Image"
        user = self.login()

        image = self._create_image()
        summary = image.get_entity_summary(user)
        self.assertHTMLEqual('<img class="entity-summary" src="%(url)s" alt="%(name)s" title="%(name)s"/>' % {
                                    'url':  image.get_dl_url(),
                                    'name': image.title,
                                },
                             summary
                            )

        casca = get_contact_model().objects.create(user=user, image=image,
                                                   first_name='Casca', last_name='Mylove',
                                                  )
        self.assertHTMLEqual(u'''<a onclick="creme.dialogs.image('%s').open();">%s</a>''' % (
                                    image.get_dl_url(),
                                    summary,
                                ),
                             field_printers_registry.get_html_field_value(casca, 'image', user)
                            )
        self.assertEqual(unicode(casca.image),
                         field_printers_registry.get_csv_field_value(casca, 'image', user)
                        )

    @skipIfCustomContact
    def test_field_printers02(self):
        "Field printer with FK on Image + credentials"
        Contact = get_contact_model()

        user = self.login(allowed_apps=['creme_core', 'persons', 'documents'])
        other_user = self.other_user

        self.role.exportable_ctypes = [ContentType.objects.get_for_model(Contact)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        create_img = self._create_image
        casca_face = create_img(title='Casca face', user=user,       description="Casca's selfie")
        judo_face  = create_img(title='Judo face',  user=other_user, description="Judo's selfie")

        self.assertTrue(other_user.has_perm_to_view(judo_face))
        self.assertFalse(other_user.has_perm_to_view(casca_face))

        create_contact = partial(Contact.objects.create, user=other_user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        get_html_val = field_printers_registry.get_html_field_value
        self.assertEqual(u'<a onclick="creme.dialogs.image(\'%s\').open();">%s</a>' % (
                                judo_face.get_dl_url(),
                                judo_face.get_entity_summary(other_user)
                            ),
                         get_html_val(judo, 'image', other_user)
                        )
        self.assertEqual('<p>Judo&#39;s selfie</p>',
                         get_html_val(judo, 'image__description', other_user)
                        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image', other_user))
        self.assertEqual(HIDDEN_VALUE, get_html_val(casca, 'image__description', other_user))

    # TODO: (block not yet injected in all apps)
    # def test_orga_block(self):
    #     self.login()
    #     orga = Organisation.objects.create(user=self.user, name='NERV')
    #     response = self.assertGET200(orga.get_absolute_url())
    #     self.assertTemplateUsed(response, 'documents/templatetags/block_linked_docs.html')

    # TODO: complete


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentQuickFormTestCase(_DocumentsTestCase):
    def quickform_data(self, count):
        return {'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   '%s' % count,
               }

    def quickform_data_append(self, data, id, user='', filedata='', folder=''):
        return data.update({'form-%d-user' % id:     user,
                            'form-%d-filedata' % id: filedata,
                            'form-%d-folder' % id:   folder,
                           }
                          )

    def test_add(self):
        user = self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = '/creme_core/quickforms/%s/%d' % (ContentType.objects.get_for_model(Document).pk, 1)
        self.assertGET200(url)

        content = 'Yes I am the content (DocumentQuickFormTestCase.test_add)'
        file_obj, file_name = self._build_filedata(content)
        folder = Folder.objects.all()[0]

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, user=user.pk, filedata=file_obj, folder=folder.pk)

        self.assertNoFormError(self.client.post(url, follow=True, data=data))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual('upload/documents/%s' % file_name, doc.filedata.name)
        # self.assertIsNone(doc.description)
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.folder)

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())


@skipIfCustomDocument
@skipIfCustomFolder
# class CSVDocumentQuickWidgetTestCase(_DocumentsTestCase):
class DocumentQuickWidgetTestCase(_DocumentsTestCase):
    # def test_add_from_widget(self):
    def test_add_csv_doc(self):
        user = self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        # url = reverse('documents__create_document_from_widget', args=(1,))
        url = reverse('documents__create_document_from_widget')
        self.assertGET200(url)

        # content = 'Content (CSVDocumentQuickWidgetTestCase.test_add_from_widget)'
        content = 'Content (DocumentQuickWidgetTestCase.test_add_csv_doc)'
        file_obj, file_name = self._build_filedata(content)
        response = self.client.post(url, follow=True,
                                    data={'user':     user.pk,
                                          'filedata': file_obj,
                                         }
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        folder = get_csv_folder_or_create(user)
        self.assertEqual('upload/documents/%s' % file_name, doc.filedata.name)
        # self.assertIsNone(doc.description)
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.folder)

        self.assertEqual(u'<json>%s</json>' % json_dump({
                                'added': [[doc.id, unicode(doc)]],
                                'value': doc.id,
                            }),
                         response.content
                        )

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc01(self):
        user = self.login()

        url = reverse('documents__create_image_popup')
        self.assertGET200(url)

        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))

        folder = Folder.objects.all()[0]
        image_file = open(path, 'rb')
        response = self.client.post(url, follow=True,
                                    data={'user':   user.pk,
                                          'image':  image_file,
                                          'folder': folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual('creme_22.png', doc.title)
        self.assertEqual('',             doc.description)
        self.assertEqual(folder,         doc.folder)
        self.assertTrue('image/png',     doc.mime_type.name)

        self.assertTrue(filecmp.cmp(path, doc.filedata.path))

        self.assertEqual(u'<json>%s</json>' % json_dump({
                                'added': [[doc.id, unicode(doc)]],
                                'value': doc.id,
                            }),
                         response.content
                        )

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc02(self):
        "Not an image file"
        user = self.login()

        folder = Folder.objects.all()[0]
        content = '<xml>Content (DocumentQuickWidgetTestCase.test_add_image_doc02)</xml>'
        file_obj, file_name = self._build_filedata(content, suffix='.xml')
        response = self.assertPOST200(reverse('documents__create_image_popup'),
                                      follow=True,
                                      data={'user':   user.pk,
                                            'image':  file_obj,
                                            'folder': folder.id,
                                           },
                                     )
        self.assertFormError(response, 'form', 'image',
                             _('Upload a valid image. '
                               'The file you uploaded was either not an image or a corrupted image.'
                              )
                            )

