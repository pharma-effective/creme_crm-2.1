QUnit.module("creme.emails.listview.actions", new QUnitMixin(QUnitEventMixin,
                                                             QUnitAjaxMixin,
                                                             QUnitListViewMixin,
                                                             QUnitDialogMixin, {
    beforeEach: function() {
        var backend = this.backend;

        this.setMockBackendPOST({
            'mock/emails/resend': function(url, data, options) {
                return backend.response(200, '');
            },
            'mock/emails/resend/fail': function(url, data, options) {
                return backend.response(400, 'invalid response !');
            }
        });
    }
}));

QUnit.test('creme.emails.ResendEMailsAction (no selection)', function(assert) {
    var list = this.createListView();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    equal(0, list.countEntities());
    deepEqual([], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedAlertDialog(gettext("Please select at least one e-mail."));
    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockRedirectCalls());
});

QUnit.test('creme.emails.ResendEMailsAction (not confirmed)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('2,3');

    equal(2, list.countEntities());
    deepEqual(['2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/emails/resend'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['cancel']], this.mockListenerCalls('action-cancel'));
    deepEqual([], this.mockBackendUrlCalls('mock/entity/delete'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));
});

QUnit.test('creme.emails.ResendEMailsAction (error)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend/fail'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2');

    equal(2, list.countEntities());
    deepEqual(['1', '2'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/emails/resend'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.acceptConfirmDialog();

    this.assertOpenedAlertDialog(undefined, gettext('Bad Request'));

    deepEqual([], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/emails/resend/fail'));
    deepEqual([], this.mockBackendUrlCalls('mock/listview/reload'));

    this.closeDialog();

    deepEqual([['fail']], this.mockListenerCalls('action-fail'));
    deepEqual([
        ['POST', {ids: '1,2'}]
    ], this.mockBackendUrlCalls('mock/emails/resend/fail'));
    deepEqual([
        ['POST', {
            sort_field: ['regular_field-name'],
            sort_order: [''],
            selected_rows: ['1,2'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});


QUnit.test('creme.emails.ResendEMailsAction (ok)', function(assert) {
    var list = this.createDefaultListView();
    var action = new creme.emails.ResendEMailsAction(list, {
        url: 'mock/emails/resend'
    }).on(this.listviewActionListeners);

    $(list).find('#selected_rows').val('1,2,3');

    equal(3, list.countEntities());
    deepEqual(['1', '2', '3'], list.getSelectedEntitiesAsArray());

    this.assertClosedDialog();

    action.start();

    this.assertOpenedDialog();
    this.acceptConfirmDialog();

    deepEqual([
        ['POST', {ids: '1,2,3'}]
    ], this.mockBackendUrlCalls('mock/emails/resend'));
    deepEqual([['done']], this.mockListenerCalls('action-done'));
    deepEqual([
        ['POST', {
            sort_field: ['regular_field-name'],
            sort_order: [''],
            selected_rows: ['1,2,3'],
            q_filter: ['{}'],
            ct_id: ['67'],
            selection: 'multiple'}]
    ], this.mockBackendUrlCalls('mock/listview/reload'));
});