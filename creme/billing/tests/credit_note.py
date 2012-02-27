# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from creme_core.models import Relation, Currency
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('CreditNoteTestCase',)


class CreditNoteTestCase(_BillingTestCase, CremeTestCase):
    def create_credit_note(self, name, source, target, currency=None, discount=Decimal(), user=None):
        user = user or self.user
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/credit_note/add', follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.id,
                                          'discount':        discount,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        credit_note = self.get_object_or_fail(CreditNote, name=name)
        self.assertTrue(response.redirect_chain[0][0].endswith('/billing/credit_note/%s' % credit_note.id))

        return credit_note

    def create_credit_note_n_orgas(self, name, user=None):
        user = user or self.user
        create = Organisation.objects.create
        source = create(user=user, name='Source Orga')
        target = create(user=user, name='Target Orga')

        credit_note = self.create_credit_note(name, source, target, user=user)

        return credit_note, source, target

    def test_createview01(self): # credit note total < billing document total where the credit note is applied
        self.login()

        self.assertEqual(200, self.client.get('/billing/credit_note/add').status_code)
        user = self.user

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        ProductLine.objects.create(user=user, related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("299"))

        # TODO the credit note must be valid : Status OK (not out of date or consumed), Target = Billing document's target and currency = billing document's currency
        # Theses rules must be applied with q filter on list view before selection
        Relation.objects.create(object_entity=invoice, subject_entity=credit_note, type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user)

        invoice = self.refresh(invoice)
        expected_total = Decimal('1')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_createview02(self): # credit note total > document billing total where the credit note is applied
        self.login()

        user = self.user
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        ProductLine.objects.create(user=user, related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("301"))

        # TODO the credit note must be valid : Status OK (not out of date or consumed), Target = Billing document's target and currency = billing document's currency
        # Theses rules must be applied with q filter on list view before selection
        Relation.objects.create(object_entity=invoice, subject_entity=credit_note, type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user)

        invoice = self.refresh(invoice)
        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    #TODO: complete (other views)