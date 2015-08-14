# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import SearchConfigItem, UserRole
    from ..base import CremeTestCase
    from ..fake_models import FakeContact as Contact, FakeOrganisation as Organisation

    #from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class SearchConfigTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls._sci_backup = list(SearchConfigItem.objects.all())
        SearchConfigItem.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        CremeTestCase.tearDownClass()
        SearchConfigItem.objects.bulk_create(cls._sci_backup)

    def test_create_if_needed01(self):
        self.assertEqual(0, SearchConfigItem.objects.count())

        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        sc_items = SearchConfigItem.objects.all()
        self.assertEqual(1, len(sc_items))

        sc_item = sc_items[0]
        self.assertEqual(Contact, sc_item.content_type.model_class())
#        self.assertIsNone(sc_item.user)
        self.assertIsNone(sc_item.role)
        self.assertIs(sc_item.superuser, False)
        self.assertEqual('first_name,last_name', sc_item.field_names)
        self.assertIs(sc_item.all_fields, False)
        self.assertIs(sc_item.disabled, False)

        sfields = sc_item.searchfields
        self.assertEqual(2, len(sfields))

        fn_field = sfields[0]
        self.assertEqual('first_name',     fn_field.name)
        self.assertEqual(_(u'First name'), fn_field.verbose_name)
        self.assertEqual(_(u'First name'), unicode(fn_field))

        ln_field = sfields[1]
        self.assertEqual('last_name',     ln_field.name)
        self.assertEqual(_(u'Last name'), ln_field.verbose_name)
        self.assertEqual(_(u'Last name'), unicode(ln_field))

        self.assertEqual(_(u'Default search configuration for "%s"') % 'Test Contact',
                         unicode(sc_item)
                        )

        SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])
        self.assertEqual(1, SearchConfigItem.objects.count())

    def test_create_if_needed02(self):
        "With a role"
        self.login()
        #user = self.user

        role = self.role
#        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name'], user)
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name'], role=role)
        self.assertIsInstance(sc_item, SearchConfigItem)

        self.assertEqual(1, SearchConfigItem.objects.count())

        self.assertEqual(Organisation, sc_item.content_type.model_class())
#        self.assertEqual(user,         sc_item.user)
        self.assertEqual(role,         sc_item.role)
        self.assertFalse(sc_item.superuser)

        self.assertEqual(_(u'Search configuration of "%(role)s" for "%(type)s"') % {
                                'role': role,
                                'type': 'Test Organisation',
                            },
                         unicode(sc_item)
                        )

    def test_create_if_needed03(self):
        "For super users"
        self.login()

        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name'], role='superuser')

        self.assertEqual(Organisation, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertTrue(sc_item.superuser)

        self.assertEqual(_(u'Search configuration of super-users for "%s"') %
                                'Test Organisation',
                         unicode(sc_item)
                        )

    def test_create_if_needed04(self):
        "Invalid fields"
        sc_item = SearchConfigItem.create_if_needed(Contact, ['invalid_field', 'first_name'])

        sfields = sc_item.searchfields
        self.assertEqual(1, len(sfields))
        self.assertEqual('first_name', sfields[0].name)

    def test_create_if_needed05(self):
        "Invalid fields : no subfield"
        sc_item = SearchConfigItem.create_if_needed(Contact, ['last_name__invalid', 'first_name'])

        sfields = sc_item.searchfields
        self.assertEqual(1, len(sfields))
        self.assertEqual('first_name', sfields[0].name)

    def test_create_if_needed06(self):
        "Disabled"
        self.login()

        sc_item = SearchConfigItem.create_if_needed(Organisation, [], disabled=True)
        self.assertTrue(sc_item.disabled)
        self.assertFalse(sc_item.field_names)

    def test_allfields01(self):
        "True"
        sc_item = SearchConfigItem.create_if_needed(Organisation, [])
        self.assertTrue(sc_item.all_fields)

        sfields = {sf.name for sf in sc_item.searchfields}
        self.assertIn('name', sfields)
#        self.assertIn('shipping_address__city', sfields)
        self.assertIn('address__city', sfields)
        self.assertNotIn('creation_date', sfields)

    def test_allfields02(self):
        "False"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])
        self.assertFalse(sc_item.all_fields)

    def test_searchfields01(self):
        "Invalid field are deleted automatically"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.field_names += ',invalid'
        sc_item.save()

        sc_item = self.refresh(sc_item) #no cache any more

        self.assertEqual(['name', 'phone'], [sf.name for sf in sc_item.searchfields])
        self.assertEqual('name,phone', sc_item.field_names)

    def test_searchfields02(self):
        "Invalid field are deleted automatically => if no more valid field, all are used"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])
        sc_item.field_names = 'invalid01,invalid02'
        sc_item.save()

        sc_item = self.refresh(sc_item) #no cache any more

        sfields = {sf.name for sf in sc_item.searchfields}
        self.assertIn('name', sfields)
        self.assertIn('capital', sfields)
        self.assertNotIn('created', sfields)

        self.assertTrue(sc_item.all_fields)
        self.assertIsNone(sc_item.field_names)

    def test_searchfields_setter01(self):
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = ['capital', 'email', 'invalid']
        sc_item.save()

        sc_item = self.refresh(sc_item)
        self.assertEqual(['capital', 'email'], [sf.name for sf in sc_item.searchfields])
        self.assertFalse(sc_item.all_fields)

        sc_item.searchfields = []
        self.assertIsNone(sc_item.field_names)
        self.assertTrue(sc_item.all_fields)

    def test_searchfields_setter02(self):
        "No fields"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = []
        sc_item.save()
        self.assertIsNone(self.refresh(sc_item).field_names)
        self.assertTrue(sc_item.all_fields)

        sc_item.searchfields = ['name']
        self.assertEqual(['name'], [sf.name for sf in sc_item.searchfields])
        self.assertFalse(sc_item.all_fields)

    def test_searchfields_setter03(self):
        "Invalid fields"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'])

        sc_item.searchfields = ['invalid']
        sc_item.save()
        self.assertIsNone(self.refresh(sc_item).field_names)

    def test_searchfields_setter04(self):
        "Fields + disabled"
        sc_item = SearchConfigItem.create_if_needed(Organisation, ['name', 'phone'],
                                                    disabled=True,
                                                   )
        self.assertEqual(['name', 'phone'], [sf.name for sf in sc_item.searchfields])

    def test_get_4_models01(self):
        "No model"
        user = self.login()

        configs = SearchConfigItem.get_4_models([], user)
        self.assertEqual([], list(configs))

    def test_get_4_models02(self):
        "One model, no config in BD"
        user = self.login()

        configs = list(SearchConfigItem.get_4_models([Contact], user))
        self.assertEqual(1, len(configs))

        sc_item = configs[0]
        self.assertIsInstance(sc_item, SearchConfigItem)
        self.assertEqual(Contact, sc_item.content_type.model_class())
        self.assertIsNone(sc_item.role)
        self.assertFalse(sc_item.superuser)
        self.assertTrue(sc_item.all_fields)
        self.assertIsNone(sc_item.pk)

    def test_get_4_models03(self):
        "One model, 1 config in DB"
        user = self.login()

        sc_item = SearchConfigItem.create_if_needed(Contact, ['first_name', 'last_name'])

        configs = list(SearchConfigItem.get_4_models([Contact], user))
        self.assertEqual(1, len(configs))
        self.assertEqual(sc_item, configs[0])

    def test_get_4_models04(self):
        "One model, 2 configs in DB"
        self.login()

        create_role = UserRole.objects.create
        role2 = create_role(name='CEO')
        role3 = create_role(name='Office lady')

        create = SearchConfigItem.create_if_needed
        create(Contact, ['description'], role='superuser')
        create(Contact, ['first_name', 'last_name'])
        create(Contact, ['first_name'], role=role2)
        sc_item = create(Contact, ['last_name'], role=self.role) # <===
        create(Contact, ['first_name', 'description'], role=role3)

        configs = list(SearchConfigItem.get_4_models([Contact], self.other_user))
        self.assertEqual(1, len(configs))
        self.assertEqual(sc_item, configs[0])

    def test_get_4_models05(self):
        "One model, 2 configs in DB (other order)"
        self.login()

        create = SearchConfigItem.create_if_needed
        sc_item = create(Contact, ['last_name'], role=self.role)
        create(Contact, ['first_name', 'last_name'])
        create(Contact, ['description'], role='superuser')

        self.assertEqual(sc_item,
                         SearchConfigItem.get_4_models([Contact], self.other_user).next()
                        )

    def test_get_4_models06(self):
        "One model, 2 configs in DB (super-user)"
        user = self.login()

        create_role = UserRole.objects.create
        role2 = create_role(name='CEO')
        role3 = create_role(name='Office lady')

        create = SearchConfigItem.create_if_needed
        create(Contact, ['first_name', 'last_name'])
        create(Contact, ['first_name'], role=role2)
        sc_item = create(Contact, ['last_name'], role='superuser') # <==
        create(Contact, ['first_name', 'description'], role=role3)

        self.assertEqual(sc_item,
                         SearchConfigItem.get_4_models([Contact], user).next()
                        )

    def test_get_4_models07(self):
        "One model, 2 configs in DB (super-user) (other order)"
        user = self.login()

        create = SearchConfigItem.create_if_needed
        sc_item = create(Contact, ['last_name'], role='superuser')
        create(Contact, ['first_name', 'last_name'])

        self.assertEqual(sc_item,
                         SearchConfigItem.get_4_models([Contact], user).next()
                        )

    def test_get_4_models08(self):
        "2 models"
        user = self.login()

        configs = list(SearchConfigItem.get_4_models([Contact, Organisation], user))
        self.assertEqual(2, len(configs))
        self.assertEqual(Contact,      configs[0].content_type.model_class())
        self.assertEqual(Organisation, configs[1].content_type.model_class())
