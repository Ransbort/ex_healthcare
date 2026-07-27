
frappe.router.on('change', () => {
    const route = frappe.get_route();
    const is_bare_desk = route.length === 0 || (route.length === 1 && ['home', 'workspace'].includes(route[0]));

    if (!is_bare_desk) return;

    if (frappe.user.has_role('Pharmacist')) {
        frappe.set_route('pharmacy-pos');
    } else if (frappe.user.has_role('Cashier')) {
        frappe.set_route('cashier-portal');
    }
});
