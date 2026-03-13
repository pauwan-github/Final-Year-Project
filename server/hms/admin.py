from django.contrib import admin
from .models import OnChainAudit
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages


@admin.register(OnChainAudit)
class OnChainAuditAdmin(admin.ModelAdmin):
	list_display = ('id', 'record_type', 'object_id', 'record_hash', 'tx_hash', 'created_at')
	readonly_fields = ('record_hash', 'tx_hash', 'created_at')
	search_fields = ('record_hash', 'tx_hash', 'record_type')
	list_filter = ('record_type',)

	class Media:
		js = ('hms/admin_authorize.js',)


class AuthorizeAddressForm(forms.Form):
	address = forms.CharField(max_length=66, label='Ethereum address')


def authorize_address_view(request):
	# We only accept POST from the admin JS button. For GET requests redirect back.
	if request.method != 'POST':
		messages.info(request, 'Use the "Authorize Address" button on the OnChainAudit admin list to authorize an address.')
		return redirect('/admin/')

	form = AuthorizeAddressForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Invalid address provided.')
		return redirect('/admin/')

	addr = form.cleaned_data['address']
	tx = None
	try:
		# Import web3 client lazily to avoid heavy imports at module import time
		from blockchain import web3_client
	except Exception as e:
		messages.error(request, f'Blockchain client unavailable: {e}')
		return redirect('/admin/')

	try:
		tx = web3_client.add_authorized_address(addr)
	except Exception as e:
		messages.error(request, f'Error sending tx: {e}')
		return redirect('/admin/')

	if tx:
		messages.success(request, f'Authorization tx sent: {tx}')
	else:
		messages.error(request, 'Could not send tx — check BLOCKCHAIN_PRIVATE_KEY and RPC settings.')
	return redirect('/admin/')


# Insert an admin URL for authorizing addresses
original_get_urls = admin.site.get_urls

def get_urls():
	urls = original_get_urls()
	my_urls = [path('hms/authorize-address/', admin.site.admin_view(authorize_address_view), name='hms-authorize-address')]
	return my_urls + urls

admin.site.get_urls = get_urls
