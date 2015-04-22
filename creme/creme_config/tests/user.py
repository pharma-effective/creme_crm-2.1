# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as jsonloads
    from unittest import skipIf

    from django.conf import settings
    from django.contrib.sessions.models import Session
    from django.utils import timezone as django_tz
    from django.utils.translation import ugettext as _

    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.core.setting_key import SettingKey
    from creme.creme_core.models import CremeUser as User
    from creme.creme_core.models import (CremeEntity, CremeProperty,
            EntityCredentials, UserRole, SetCredentials, Mutex, SettingValue) #Relation
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.tests.base import skipIfCustomOrganisation
    from creme.persons.constants import REL_SUB_EMPLOYED_BY, REL_SUB_MANAGES
    from creme.persons.models import Contact, Organisation

    from ..blocks import UsersBlock, TeamsBlock, UserPreferedMenusBlock, BlockMypageLocationsBlock
    from ..constants import USER_THEME_NAME, USER_TIMEZONE
    from ..utils import get_user_theme
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('UserTestCase', 'UserSettingsTestCase')


def skipIfNotCremeUser(test_func):
    return skipIf(settings.AUTH_USER_MODEL != 'creme_core.CremeUser',
                  "Skip this test which uses CremeUser model"
                 )(test_func)


@skipIfCustomOrganisation
class UserTestCase(CremeTestCase):
    ADD_URL = '/creme_config/user/add/'
    ADD_TEAM_URL = '/creme_config/team/add/'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'persons')

    def _build_delete_url(self, user):
        return '/creme_config/user/delete/%s' % user.id

    def _build_edit_url(self, user_id, password=None):
        return '/creme_config/user/edit/%s%s' % ('password/' if password else '', user_id)

    def _build_activation_url(self, user_id, activation):
        return '/creme_config/user/%s/%s' % (activation, user_id)

    def login_not_as_superuser(self):
        apps = ('creme_config',)
        return self.login(is_superuser=False, allowed_apps=apps, admin_4_apps=apps)

    def _aux_test_portal(self):
        response = self.assertGET200('/creme_config/user/portal/')
        self.assertContains(response, 'id="%s"' % UsersBlock.id_)
        self.assertContains(response, 'id="%s"' % TeamsBlock.id_)

    def test_portal01(self):
        self.login()
        self._aux_test_portal()

    def test_portal02(self):
        self.login_not_as_superuser()
        self._aux_test_portal()

    @skipIfNotCremeUser
    def test_create01(self):
        self.login()

        url = self.ADD_URL
        self.assertGET200(url)

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username   = 'deunan'
        first_name = 'Deunan'
        last_name  = u'Knut'
        password   = 'password'
        email      = 'd.knut@eswat.ol'
        response = self.client.post(url, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'first_name':   first_name,
                                          'last_name':    last_name,
                                          'email':        email,
                                          'is_superuser': True,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_EMPLOYED_BY,
                                         }
                                   )
        self.assertNoFormError(response)

        users = User.objects.filter(username=username)
        self.assertEqual(1, len(users))

        user = users[0]
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.role)
        self.assertEqual(first_name, user.first_name)
        self.assertEqual(last_name,  user.last_name)
        self.assertEqual(email,      user.email)
        self.assertTrue(user.check_password(password))

        contact = self.get_object_or_fail(Contact, is_user=user,
                                          first_name=first_name,
                                          last_name=last_name,
                                          email=email,
                                         )
        self.assertRelationCount(1, contact, REL_SUB_EMPLOYED_BY, orga)

    @skipIfNotCremeUser
    def test_create02(self):
        "Not superuser ; special chars in username"
        self.login()

        role = UserRole(name='Mangaka')
        role.allowed_apps = ['persons']
        role.save()

        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'dknut@eswat.ol'
        password = 'password'
        first_name = 'Deunan'
        last_name = u'Knut'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'first_name':   first_name,
                                          'last_name':    last_name,
                                          'email':        username,
                                          'role':         role.id,
                                          #'contact':      contact.id,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertNoFormError(response)

        user = self.get_object_or_fail(User, username=username)
        self.assertEqual(role,     user.role)

        self.assertTrue(user.has_perm_to_view(orga))

        contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
        self.assertEqual(user, contact.is_user)
        self.assertRelationCount(1, contact, REL_SUB_MANAGES, orga)

    @skipIfNotCremeUser
    def test_create03(self):
        "First name, last name, email, orga, rtypes are required"
        self.login()

        password = 'password'
        response = self.assertPOST200(self.ADD_URL, follow=True,
                                      data={'username':     'deunan',
                                            'password_1':   password,
                                            'password_2':   password,
                                            'is_superuser': True,
                                           }
                                      )

        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'first_name',   msg)
        self.assertFormError(response, 'form', 'last_name',    msg)
        self.assertFormError(response, 'form', 'email',        msg)
        self.assertFormError(response, 'form', 'organisation', msg)
        self.assertFormError(response, 'form', 'relation',     msg)

    @skipIfNotCremeUser
    def test_create04(self):
        user = self.login_not_as_superuser()

        url = self.ADD_URL
        self.assertGET403(url)

        orga = Organisation.objects.create(user=user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        password = 'password'
        self.assertPOST403(url, data={'username':     'deunan',
                                      'password_1':   password,
                                      'password_2':   password,
                                      'first_name':   'Deunan',
                                      'last_name':    'Knut',
                                      'email':        'd.knut@eswat.ol',
                                      'is_superuser': False,
                                      'organisation': orga.id,
                                      'relation':     REL_SUB_EMPLOYED_BY,
                                     }
                          )

    @skipIfNotCremeUser
    def test_create05(self):
        "Wrong username"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'é^ǜù'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'is_superuser': True,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertFormError(response, 'form', 'username',
                             _("This value may contain only letters, numbers and @/./+/-/_ characters.")
                            )

    @skipIfNotCremeUser
    def test_create06(self):
        "Common user without role"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'is_superuser': False,
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_MANAGES,
                                         }
                                   )
        self.assertFormError(response, 'form', 'role', 
                             _(u"Choose a role or set superuser status to 'True'.")
                            )

    @skipIfNotCremeUser
    def test_create07(self):
        "Password errors"
        user = self.login()

        url = self.ADD_URL

        orga = Organisation.objects.create(user=user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        data = {'username':     'deunan',
                'first_name':   'Deunan',
                'last_name':    'Knut',
                'email':        'd.knut@eswat.ol',
                'is_superuser': True,
                'organisation': orga.id,
                'relation':     REL_SUB_EMPLOYED_BY,
               }
        response = self.assertPOST200(url, follow=True, data=data)
        msg = _('This field is required.')
        self.assertFormError(response, 'form', 'password_1', msg)
        self.assertFormError(response, 'form', 'password_2', msg)

        response = self.assertPOST200(url, follow=True,
                                      data=dict(data, password_1='passwd'),
                                     )
        self.assertFormError(response, 'form', 'password_2', msg)

        response = self.assertPOST200(url, follow=True,
                                      data=dict(data, password_2='passwd'),
                                     )
        self.assertFormError(response, 'form', 'password_1', msg)

        response = self.assertPOST200(url, follow=True,
                                      data=dict(data,
                                                password_1='password',
                                                password_2='passwd',
                                               ),
                                     )
        self.assertFormError(response, 'form', 'password_2', _('Passwords are different'))

    @skipIfNotCremeUser
    def test_create08(self):
        "Unique username"
        user = self.login()

        orga = Organisation.objects.create(user=user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        password = 'password'
        response = self.assertPOST200(self.ADD_URL,
                                      data={'username':     user.username,
                                            'password_1':   password,
                                            'password_2':   password,
                                            'first_name':   user.first_name,
                                            'last_name':    user.last_name,
                                            'email':        'd.knut@eswat.ol',
                                            'is_superuser': True,
                                            'organisation': orga.id,
                                            'relation':     REL_SUB_EMPLOYED_BY,
                                           }
                                     )
        self.assertFormError(response, 'form', 'username',
                             _(u'%(model_name)s with this %(field_label)s already exists.') % {
                                    'model_name':  _('User'),
                                    'field_label': _('Username'),
                                }
                            )

    @skipIfNotCremeUser
    def test_create11(self):
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Olympus')
        CremeProperty.objects.create(creme_entity=orga, type_id=PROP_IS_MANAGED_BY_CREME)

        username = 'deunan'
        password = 'password'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'username':     username,
                                          'password_1':   password,
                                          'password_2':   password,
                                          'first_name':   'Deunan',
                                          'last_name':    'Knut',
                                          'email':        'd.knut@eswat.ol',
                                          'is_superuser': True,
                                          'role':         self.role.id, # <==
                                          'organisation': orga.id,
                                          'relation':     REL_SUB_EMPLOYED_BY,
                                         }
                                   )
        self.assertNoFormError(response)

        user = self.get_object_or_fail(User, username=username)
        self.assertTrue(user.is_superuser)
        self.assertIsNone(user.role)

    @skipIfNotCremeUser
    def test_edit01(self):
        user = self.login()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', first_name='??', last_name='??',
                                         email='??', role=role1,
                                        )
        deunan = other_user.linked_contact

        briareos = Contact.objects.create(user=user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGET200(url)

        first_name = 'Deunan'
        last_name  = 'Knut'
        email      = 'd.knut@eswat.ol'
        role2 = UserRole.objects.create(name='Slave')
        response = self.client.post(url, follow=True,
                                    data={'first_name': first_name,
                                          'last_name':  last_name,
                                          'email':      email,
                                          'role':       role2.id,
                                         }
                                   )
        self.assertNoFormError(response)

        other_user = self.refresh(other_user)
        self.assertEqual(first_name, other_user.first_name)
        self.assertEqual(last_name,  other_user.last_name)
        self.assertEqual(email,      other_user.email)
        self.assertEqual(role2,      other_user.role)

        briareos = self.refresh(briareos) #refresh cache
        self.assertFalse(other_user.has_perm_to_view(briareos))

        #contact is synced
        deunan = self.refresh(deunan)
        self.assertEqual(first_name,  deunan.first_name)
        self.assertEqual(last_name,   deunan.last_name)
        self.assertEqual(email,       deunan.email)
        #self.assertEqual(description, deunan.description)

    @skipIfNotCremeUser
    def test_edit02(self):
        "Can not edit a team with the user edit view"
        self.login()

        user = User.objects.create_user(username='deunan',
                                             first_name='Deunan',
                                             last_name='Knut',
                                             email='d.knut@eswat.ol',
                                             password='uselesspw',
                                            )
        team  = self._create_team('Teamee', [user])

        url = self._build_edit_url(team.id)
        self.assertGET404(url)
        self.assertPOST404(url)

    @skipIfNotCremeUser
    def test_edit03(self):
        user = self.login_not_as_superuser()

        role1 = UserRole(name='Master')
        role1.allowed_apps = ['persons']
        role1.save()
        SetCredentials.objects.create(role=role1, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_ALL
                                     )
        other_user = User.objects.create(username='deunan', role=role1)

        briareos = Contact.objects.create(user=user, first_name='Briareos', last_name='Hecatonchires')
        self.assertTrue(other_user.has_perm_to_view(briareos))

        url = self._build_edit_url(other_user.id)
        self.assertGET403(url)

        role2 = UserRole.objects.create(name='Slave')
        self.assertPOST403(url, data={'first_name': 'Deunan',
                                      'last_name':  'Knut',
                                      'email':      'd.knut@eswat.ol',
                                      'role':       role2.id,
                                     }
                          )

    @skipIfNotCremeUser
    def test_edit04(self):
        "Common user without role"
        self.login()

        other_user = self.other_user
        role = other_user.role
        self.assertIsNotNone(role)

        url = self._build_edit_url(other_user.id)
        self.assertGET200(url)

        response = self.client.post(url, follow=True, data={'is_superuser': ''})
        self.assertFormError(response, 'form', 'role',
                             _(u"Choose a role or set superuser status to 'True'.")
                            )

        response = self.client.post(url, follow=True,
                                    data={'is_superuser': 'on',
                                          'role':         role.id,
                                         },
                                   )
        self.assertNoFormError(response)

        other_user = self.refresh(other_user)
        self.assertTrue(other_user.is_superuser)
        self.assertIsNone(other_user.role)

    @skipIfNotCremeUser
    def test_change_password01(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        password = 'password'
        response = self.client.post(url, follow=True,
                                    data={'password_1': password,
                                          'password_2': password,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertTrue(self.refresh(other_user).check_password(password))

    @skipIfNotCremeUser
    def test_change_password02(self):
        self.login_not_as_superuser()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET403(url)

        password = 'password'
        self.assertPOST403(url, data={'password_1': password,
                                      'password_2': password,
                                     }
                          )

    @skipIfNotCremeUser
    def test_change_password03(self):
        self.login()

        other_user = User.objects.create(username='deunan')
        url = self._build_edit_url(other_user.id, password=True)
        self.assertGET200(url)

        password = 'password'
        response = self.client.post(url, follow=True,
                                    data={'password_1': password,
                                          'password_2': password + '42',
                                         }
                                   )
        self.assertFormError(response, 'form', 'password_2', _(u"Passwords are different"))

    @skipIfNotCremeUser
    def test_user_activation01(self):
        "Not superuser"
        self.login_not_as_superuser()
        other_user = User.objects.create(username='deunan')
        url = partial(self._build_activation_url, other_user.id)
        self.assertGET403(url('deactivate'))
        self.assertGET403(url('activate'))

    @skipIfNotCremeUser
    def test_user_activation02(self):
        "Post only & Current user"
        user = self.login()
        url = self._build_activation_url(user.id, 'deactivate')
        self.assertGET404(url)
        self.assertPOST409(url)

    @skipIfNotCremeUser
    def test_user_activation03(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan', is_staff=True)
        url = partial(self._build_activation_url, other_user.id)
        self.assertPOST(400, url('activate'))
        self.assertPOST(400, url('deactivate'))

    @skipIfNotCremeUser
    def test_user_activation04(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan', is_staff=True)
        url = partial(self._build_activation_url, other_user.id)
        self.assertPOST(400, url('activate'))
        self.assertPOST(400, url('deactivate'))

    @skipIfNotCremeUser
    def test_user_activation05(self):
        "user is staff"
        self.login()
        other_user = User.objects.create(username='deunan')
        url = partial(self._build_activation_url, other_user.id)

        self.assertPOST200(url('deactivate'))
        self.assertFalse(self.refresh(other_user).is_active)
        self.assertPOST200(url('activate'))
        self.assertTrue(self.refresh(other_user).is_active)

    @skipIfNotCremeUser
    def test_team_create01(self):
        self.login()

        url = self.ADD_TEAM_URL
        self.assertGET200(url)

        create_user = User.objects.create_user
        user01 = create_user(username='Shogun',
                             first_name='Choji', last_name='Ochiai',
                             email='shogun@century.jp', password='uselesspw',
                            )
        user02 = create_user(username='Yukiji',
                             first_name='Yukiji', last_name='Setoguchi',
                             email='yukiji@century.jp', password='uselesspw',
                            )

        username   = 'Team-A'
        response = self.client.post(url, follow=True,
                                    data={'username':  username,
                                          'teammates': [user01.id, user02.id],
                                         }
                                   )
        self.assertNoFormError(response)

        teams = User.objects.filter(is_team=True)
        self.assertEqual(1, len(teams))

        team = teams[0]
        self.assertFalse(team.is_superuser)
        self.assertEqual('',  team.first_name)
        self.assertEqual('',  team.last_name)
        self.assertEqual('',  team.email)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user01.id, teammates)
        self.assertIn(user02.id, teammates)

        self.assertFalse(Contact.objects.filter(is_user=team))

    @skipIfNotCremeUser
    def test_team_create02(self):
        self.login_not_as_superuser()

        url = self.ADD_TEAM_URL
        self.assertGET403(url)

        user01 = User.objects.create_user(username='Shogun',
                                          first_name='Choji', last_name='Ochiai',
                                          email='shogun@century.jp', password='uselesspw',
                                         )
        self.assertPOST403(url, data={'username':  'Team-A',
                                      'teammates': [user01.id],
                                     }
                          )

    def _create_team(self, name, teammates):
        team = User.objects.create(username=name, is_team=True, role=None)
        team.teammates = teammates

        return team

    @skipIfNotCremeUser
    def test_team_edit01(self):
        self.login()

        role = UserRole(name='Role')
        role.allowed_apps = ['creme_core']
        role.save()
        SetCredentials.objects.create(role=role, value=EntityCredentials.VIEW,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        def create_user(name, email):
            user = User.objects.create_user(username=name, email=email,
                                            first_name=name, last_name='Endou',
                                            password='uselesspw'
                                           )
            user.role = role
            user.save()

            return user

        user01 = create_user('Maruo',   'maruo@century.jp')
        user02 = create_user('Yokiji',  'yokiji@century.jp')
        user03 = create_user('Koizumi', 'koizumi@century.jp')

        self.assertGET404('/creme_config/team/edit/%s' % user01.id)

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        entity = CremeEntity.objects.create(user=team)
        self.assertTrue(user01.has_perm_to_view(entity))
        self.assertTrue(user02.has_perm_to_view(entity))
        self.assertFalse(user03.has_perm_to_view(entity))

        url = '/creme_config/team/edit/%s' % team.id
        self.assertGET200(url)

        teamname += '_edited'
        response = self.client.post(url, follow=True,
                                    data={'username':  teamname,
                                          'teammates': [user02.id, user03.id],
                                        }
                                   )
        self.assertNoFormError(response)

        team = self.refresh(team)
        self.assertEqual(teamname, team.username)

        teammates = team.teammates
        self.assertEqual(2, len(teammates))
        self.assertIn(user02.id, teammates)
        self.assertIn(user03.id, teammates)
        self.assertNotIn(user01.id, teammates)

        #credentials have been updated ?
        entity = CremeEntity.objects.get(pk=entity.id)
        self.assertFalse(self.refresh(user01).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user02).has_perm_to_view(entity))
        self.assertTrue(self.refresh(user03).has_perm_to_view(entity))

    @skipIfNotCremeUser
    def test_team_edit02(self):
        self.login_not_as_superuser()

        create_user = User.objects.create_user
        user01 = create_user(username='Shogun',
                             first_name='Choji', last_name='Ochiai',
                             email='shogun@century.jp', password='uselesspw',
                            )
        user02 = create_user(username='Yukiji',
                             first_name='Yukiji', last_name='Setoguchi',
                             email='yukiji@century.jp', password='uselesspw',
                            )

        teamname = 'Teamee'
        team = self._create_team(teamname, [user01, user02])

        url = '/creme_config/team/edit/%s' % team.id
        self.assertGET403(url)
        self.assertPOST403(url, data={'username':  teamname,
                                      'teammates': [user02.id],
                                     }
                          )

    @skipIfNotCremeUser
    def test_team_delete01(self):
        self.login()

        user = User.objects.create_user(username='Shogun',
                                             first_name='Choji', last_name='Ochiai',
                                             email='shogun@century.jp',
                                             password='uselesspw',
                                            )
        team = self._create_team('Teamee', [])

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_team_delete02(self):
        self.login()

        user = User.objects.create_user(username='Shogun',
                                             first_name='Choji', last_name='Ochiai',
                                             email='shogun@century.jp',
                                             password='uselesspw',
                                            )
        team  = self._create_team('Teamee', [user])
        team2 = self._create_team('Teamee2', [user])

        ce = CremeEntity.objects.create(user=team)

        url = self._build_delete_url(team)
        self.assertGET200(url)
        self.assertPOST200(url, data={'to_user': team2.id})
        self.assertDoesNotExist(team)

        ce = self.assertStillExists(ce)
        self.assertEqual(team2, ce.user)

    @skipIfNotCremeUser
    def test_team_delete03(self):
        self.login()

        team = self._create_team('Teamee', [])
        CremeEntity.objects.create(user=team)

        self.assertPOST200(self._build_delete_url(team), data={'to_user': self.user.id})
        self.assertDoesNotExist(team)

    @skipIfNotCremeUser
    def test_team_delete04(self):
        self.login_not_as_superuser()

        user = User.objects.create_user(username='Shogun',
                                        first_name='Choji', last_name='Ochiai',
                                        email='shogun@century.jp',
                                        #password='uselesspw',
                                       )
        team = self._create_team('Teamee', [])

        url = self._build_delete_url(team)
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})

    @skipIfNotCremeUser
    def test_user_delete01(self):
        "Delete view can delete a superuser if at least one remains"
        user = self.login()
        root = self.get_object_or_fail(User, username='root')

        self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        self.assertEqual(1, User.objects.exclude(id=user.id).filter(is_superuser=True).count())

        url = self._build_delete_url(root)
        self.assertGET200(url)

        self.assertPOST200(url, {'to_user': user.id})
        self.assertEqual(1, User.objects.filter(is_superuser=True).count())
        self.assertDoesNotExist(root)

    @skipIfNotCremeUser
    def test_user_delete02(self):
        "Delete view can delete any normal user"
        user = self.login()
        self.assertTrue(user.is_superuser)

        other_user = self.other_user
        self.assertFalse(other_user.is_superuser)

        ce = CremeEntity.objects.create(user=other_user)

        url = self._build_delete_url(other_user)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, {'to_user': user.id}))
        self.assertDoesNotExist(other_user)

        ce = self.assertStillExists(ce)
        self.assertEqual(user, ce.user)

    @skipIfNotCremeUser
    def test_user_cannot_delete_last_superuser(self):
        "Delete view can not delete the last superuser"
        self.client.login(username='root', password='root')

        superusers = User.objects.filter(is_superuser=True)
        self.assertEqual(1, len(superusers))

        user = superusers[0]

        url = self._build_delete_url(user)
        self.assertGET409(url)
        self.assertPOST409(url, {'to_user': user.id})

        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_user_cannot_delete_staff_user(self):
        "Delete view can not delete the staff user"
        self.login()
        hybird = User.objects.create(username='hybird', is_staff=True)

        url = self._build_delete_url(hybird)
        self.assertGET(400, url)
        self.assertPOST(400, url, {'to_user': hybird.id})

    @skipIfNotCremeUser
    def test_user_cannot_delete_during_transfert(self):
        "Delete view is protected by a lock"
        user = self.login()
        root = self.get_object_or_fail(User, username='root')

        #self.assertEqual(2, User.objects.filter(is_superuser=True).count())
        #self.assertEqual(1, User.objects.exclude(id=user.id).filter(is_superuser=True).count())
        superusers = list(User.objects.filter(is_superuser=True))
        self.assertEqual(2, len(superusers))
        self.assertIn(user, superusers)

        Mutex.get_n_lock('creme_config-forms-user-transfer_user')

        url = self._build_delete_url(root)
        self.assertGET200(url)
        self.assertPOST(400, url, {'to_user': user.id})

        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            #NB: Postgresql cancels all remaining queries after the error...
            self.assertEqual(2, User.objects.filter(is_superuser=True).count())

    @skipIfNotCremeUser
    def test_user_delete_errors(self):
        "Validation errors"
        user = self.login()
        root = User.objects.get(username='root')

        count = User.objects.count()
        self.assertGreater(count, 1)

        url = self._build_delete_url(root)
        self.assertGET200(url)

        response = self.assertPOST200(url) #no data
        self.assertFormError(response, 'form', 'to_user', _(u'This field is required.'))
        self.assertEqual(count, User.objects.count())

        response = self.assertPOST200(url, {'to_user': root.id}) #cannot move entities to deleted user
        self.assertFormError(response, 'form', 'to_user',
                             _(u'Select a valid choice. That choice is not one of the available choices.')
                            )
        self.assertStillExists(user)

    @skipIfNotCremeUser
    def test_user_delete_settingkey(self):
        "Related SettingValues are deleted."
        user = self.login()

        sk = SettingKey(id='unit_test-test_userl_delete06', description="",
                        app_label='creme_config', type=SettingKey.BOOL,
                       ) #NB: we do not ne to register it (because the SettingValue's value is not used)
        sv = SettingValue.objects.create(key=sk, user=self.other_user, value=True)

        self.assertNoFormError(self.client.post(self._build_delete_url(self.other_user),
                                                {'to_user': user.id}
                                               )
                              )
        self.assertDoesNotExist(self.other_user)
        self.assertDoesNotExist(sv)

    @skipIfNotCremeUser
    def test_user_delete_credentials(self):
        "Only super user are allowed"
        user = self.login_not_as_superuser()

        url = self._build_delete_url(self.other_user)
        self.assertGET403(url)
        self.assertPOST403(url, data={'to_user': user.id})


class UserSettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core')

    def setUp(self):
        self.login()

    def test_user_settings(self):
        response = self.assertGET200('/creme_config/my_settings/')
        self.assertContains(response, 'id="%s"' % UserPreferedMenusBlock.id_)
        self.assertContains(response, 'id="%s"' % BlockMypageLocationsBlock.id_)

    def test_change_theme01(self):
        self.assertFalse(SettingValue.objects.filter(user=self.user, key_id=USER_THEME_NAME))

        def change_theme(theme):
            self.assertPOST200('/creme_config/my_settings/set_theme/', data={'theme': theme})

            svalues = SettingValue.objects.filter(user=self.user, key_id=USER_THEME_NAME)
            self.assertEqual(1, len(svalues))
            self.assertEqual(theme, svalues[0].value)

        change_theme("chantilly")
        change_theme("icecream")

    def test_get_user_theme01(self):
        user = self.user

        class FakeRequest(object):
            def __init__(self):
                self.user = user
                self.session = {}

        self.assertFalse(SettingValue.objects.filter(user=user, key_id=USER_THEME_NAME))

        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(FakeRequest()))
        sv = self.get_object_or_fail(SettingValue, user=user, key_id=USER_THEME_NAME)

        sv.value = "unknown theme"
        sv.save()
        self.assertEqual(settings.DEFAULT_THEME, get_user_theme(FakeRequest()))

    def test_get_user_theme02(self):
        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_theme():
            try:
                theme = FakeRequest().session['usertheme']
            except Exception:
                theme = None

            return theme

        self.assertFalse(SettingValue.objects.filter(user=self.user, key_id=USER_THEME_NAME))
        self.assertIsNone(get_theme())

        self.client.get('/')
        self.get_object_or_fail(SettingValue, user=self.user, key_id=USER_THEME_NAME)
        self.assertEqual(settings.DEFAULT_THEME, get_theme())

    def test_change_timezone01(self):
        self.assertFalse(SettingValue.objects.filter(user=self.user, key_id=USER_TIMEZONE))

        #TODO: use 'nonlocal' in py3k
        inner = {'called':       False,
                 'activated_tz': None,
                }

        def fake_activate(tz):
            inner['called']       = True
            inner['activated_tz'] = tz

        django_tz.activate = fake_activate

        self.client.get('/')
        self.assertFalse(inner['called'])

        url = '/creme_config/my_settings/set_timezone/'

        def assertSelected(selected_tz):
            response = self.assertGET200(url)

            with self.assertNoException():
                form_str = jsonloads(response.content)['form']

            for line in form_str.split('\n'):
                if selected_tz in line:
                    option = line
                    break
            else:
                self.fail('Option not found')

            self.assertEqual(1, option.count('<option '))
            self.assertIn('selected', option)

        def change_tz(tz):
            self.assertPOST200(url, data={'time_zone': tz})

            svalues = SettingValue.objects.filter(user=self.user, key_id=USER_TIMEZONE)
            self.assertEqual(1, len(svalues))
            self.assertEqual(tz, svalues[0].value)

            self.client.get('/')
            self.assertTrue(inner['called'])
            self.assertEqual(tz, inner['activated_tz'])

            inner['called'] = False

        TIME_ZONE = settings.TIME_ZONE
        time_zones = [tz for tz in ('Asia/Tokyo', 'US/Eastern', 'Europe/Paris')
                        if tz != TIME_ZONE
                     ]

        assertSelected(TIME_ZONE)

        tz = time_zones[0]
        change_tz(tz)
        assertSelected(tz)

        change_tz(time_zones[1])
