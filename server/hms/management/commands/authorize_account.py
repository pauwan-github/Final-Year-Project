from django.core.management.base import BaseCommand, CommandError
from server.blockchain import web3_client

class Command(BaseCommand):
    help = 'Authorize a blockchain account address in the AuditLog contract (sends a tx).\nUsage: manage.py authorize_account 0x...'

    def add_arguments(self, parser):
        parser.add_argument('address', type=str, help='Ethereum address to authorize (0x...)')

    def handle(self, *args, **options):
        addr = options['address']
        try:
            tx = web3_client.add_authorized_address(addr)
        except Exception as e:
            raise CommandError(f'Error sending tx: {e}')

        if not tx:
            raise CommandError('Transaction was not sent. Is BLOCKCHAIN_PRIVATE_KEY and RPC configured?')

        self.stdout.write(self.style.SUCCESS(f'Authorization transaction sent: {tx}'))
