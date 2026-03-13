import os
import hashlib
from django.test import TestCase, override_settings
from django.conf import settings
from unittest.mock import patch

from .models import Patient, OnChainAudit
from ..blockchain import web3_client


class OnChainAuditTests(TestCase):
	def test_patient_save_creates_onchain_audit_and_calls_send_tx(self):
		# Patch the web3_client.send_hash_transaction to avoid real network calls
		with patch('server.blockchain.web3_client.send_hash_transaction') as mock_send:
			mock_send.return_value = '0xdeadbeef'

			p = Patient.objects.create(
				first_name='Test', last_name='User', email='t@example.com', phone='123',
				date_of_birth='1990-01-01', gender='other', address='Here',
				emergency_contact_name='EC', emergency_contact_phone='999', emergency_contact_relationship='friend'
			)

			# There should be an OnChainAudit created for the Patient
			audits = OnChainAudit.objects.filter(record_type='Patient', object_id=p.pk)
			self.assertTrue(audits.exists(), 'Expected an OnChainAudit row for saved Patient')
			audit = audits.first()
			self.assertTrue(audit.record_hash.startswith('0x') and len(audit.record_hash) == 66)
			# tx_hash should be set to the mocked return value
			self.assertEqual(audit.tx_hash, '0xdeadbeef')


	def test_send_hash_transaction_integration_conditionally(self):
		# This test runs only if RUN_HARDHAT_TESTS=1 and necessary env vars are set
		run_live = os.environ.get('RUN_HARDHAT_TESTS') == '1'
		if not run_live:
			self.skipTest('Skipping live Hardhat integration test (env RUN_HARDHAT_TESTS not set)')

		# Requires RPC and PRIVATE_KEY to be set in env
		rpc = os.environ.get('BLOCKCHAIN_RPC_URL')
		pk = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
		if not rpc or not pk:
			self.skipTest('BLOCKCHAIN_RPC_URL or BLOCKCHAIN_PRIVATE_KEY not configured')

		# Call send_hash_transaction with a dummy hash and expect a tx hash string
		dummy_hash = '0x' + hashlib.sha256(b'test').hexdigest()
		tx = web3_client.send_hash_transaction(dummy_hash)
		self.assertIsNotNone(tx)
		self.assertTrue(isinstance(tx, str) and tx.startswith('0x'))
