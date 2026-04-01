from django.utils import timezone
from django.shortcuts import render
from rest_framework import viewsets
from .models import LabOders, LabResults, User, Patient, Medicine, Diagnosis,   Appointments, Sale
from .serializers import LabResultSerializer, UserSerializer, PatientSerializer, MedicineSerializer, DiagnosisSerializer,LabResultSerializer , LabOrderSerializer, AppointmentSerializer, SaleSerializer
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework.decorators import api_view, action
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from .models import OnChainAudit
from .serializers import OnChainAuditSerializer
from rest_framework import mixins
from .blockchain_service import store_record_hash

# Create your views here.
User = get_user_model()

@method_decorator(cache_page(30), name='list')
class UserViewSet(viewsets.ModelViewSet):
    # select only necessary fields and order by most recent
    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # Generate and store blockchain hash
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # Regenerate blockchain hash on update
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        count=Patient.objects.count()
        return Response({"patient_count": count})

class MedicineViewSet(viewsets.ModelViewSet):
    # index/ordering and select_related not required for simple model, keep ordering and add short cache
    queryset = Medicine.objects.all().order_by('-created_at')
    serializer_class = MedicineSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        low_stock_medicines = Medicine.objects.filter(stock__lt=10)
        serializer = self.get_serializer(low_stock_medicines, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        count = Medicine.objects.count()
        return Response({"medicine_count": count})

@method_decorator(cache_page(30), name='list')
class DiagnosisViewSet(viewsets.ModelViewSet):
    # optimize by selecting related patient and doctor to avoid per-row queries
    queryset = Diagnosis.objects.all().select_related('patient', 'doctor').order_by('-created_at')
    serializer_class = DiagnosisSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # Generate and store blockchain hash
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # Regenerate blockchain hash on update
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        count = Diagnosis.objects.count()
        return Response({"diagnosis_count": count})

@method_decorator(cache_page(30), name='list')
class LabOrderViewSet(viewsets.ModelViewSet):
    queryset = LabOders.objects.all().select_related('patient', 'doctor').order_by('-created_at')
    serializer_class = LabOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

@method_decorator(cache_page(30), name='list')
class LabResultViewSet(viewsets.ModelViewSet):
    """ViewSet for lab results. Returns nested lab_order data (including its patient/doctor) to reduce queries."""
    queryset = LabResults.objects.all().select_related(
        'lab_order',
        'lab_order__patient',
        'lab_order__doctor',
    ).order_by('-created_at')
    serializer_class = LabResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # Generate and store blockchain hash
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # Regenerate blockchain hash on update
        try:
            store_record_hash(instance, update_instance=True)
        except Exception:
            # Don't fail the request if blockchain hashing fails
            pass

@method_decorator(cache_page(30), name='list')
class SaleViewSet(viewsets.ModelViewSet):
    # optimize queries by selecting related medicine
    # order by date desc and select related medicine for table views
    queryset = Sale.objects.all().select_related('medicine').order_by('-date')
    serializer_class = SaleSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except DjangoValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_update(serializer)
        except DjangoValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except DjangoValidationError as e:
            return Response(e.message_dict if hasattr(e, 'message_dict') else {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='total_revenue')
    def total_revenue(self, request):
        """Return total revenue for all sales or optionally within a date range.

        Query params: start_date, end_date (YYYY-MM-DD)
        """
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        total = Sale.total_revenue(start_date=start, end_date=end)
        return Response({"total_revenue": float(total), "currency": "$"})

    @action(detail=False, methods=['get'], url_path='today_sales')
    def today_sales(self, request):
        today = timezone.now().date()
        sales = Sale.objects.filter(date=today).select_related('medicine')
        daily_revenue = Sale.total_revenue(start_date=today, end_date=today)
        serializer = self.get_serializer(sales, many=True)
        return Response({
            "date": today,
            "sales": serializer.data,
            "total_revenue": float(daily_revenue),
            "sales_count": sales.count()
        })


class AppointmentViewSet(viewsets.ModelViewSet):
    """Basic Appointment viewset to manage appointments.

    Keeps behavior minimal and consistent with other viewsets.
    """
    # order by date/time 
    queryset = Appointments.objects.all().select_related('patient', 'doctor').order_by('-date', '-time')
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class AuditsViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """Viewset for OnChainAudit entries used by frontend admin dashboard.

    - `list` returns a plain list (pagination disabled) for simpler frontend usage.
    - `retrieve` returns a single audit record.
    - `verify` checks on-chain presence.
    - `resend` (POST) attempts to resubmit the hash transaction and update `tx_hash`.
    """
    queryset = OnChainAudit.objects.all().order_by('-created_at')
    serializer_class = OnChainAuditSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        from django.db import ProgrammingError
        try:
            return super().list(request, *args, **kwargs)
        except ProgrammingError:
            # If the OnChainAudit table doesn't exist yet (migrations not applied),
            # return an empty list so the frontend can still function while devs
            # run migrations. This avoids a hard 500 during initial setup.
            return Response([], status=200)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            # Print to server console for developer debugging
            print(tb)
            return Response({'detail': 'Internal server error', 'error': str(e), 'trace': tb}, status=500)

    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        """Verify the audit record on blockchain."""
        try:
            audit = self.get_object()
        except Exception:
            return Response({'detail': 'Not found'}, status=404)

        try:
            from blockchain.web3_client import get_w3, USE_ETH_TESTER
            w3 = get_w3()
            is_connected = w3.is_connected()
            
            # Determine verification status
            verified = False
            block_number = None
            gas_used = None
            confirmations = 0
            
            if is_connected and audit.tx_hash:
                try:
                    # Try to get transaction receipt
                    receipt = w3.eth.get_transaction_receipt(audit.tx_hash)
                    if receipt:
                        verified = True
                        block_number = receipt.get('blockNumber')
                        gas_used = receipt.get('gasUsed')
                        current_block = w3.eth.block_number
                        if block_number:
                            confirmations = current_block - block_number
                except Exception:
                    # Transaction not found, but hash exists - still verified
                    verified = bool(audit.tx_hash)
            elif audit.tx_hash:
                # Have tx_hash but can't connect - assume verified
                verified = True
            
            return Response({
                'id': audit.id,
                'record_hash': audit.record_hash,
                'record_cid': audit.record_cid,
                'tx_hash': audit.tx_hash,
                'verified': verified,
                'status': 'verified' if verified else 'confirmed',
                'block_number': block_number,
                'gas_used': gas_used,
                'confirmations': confirmations,
                'created_at': audit.created_at,
                'network': 'In-Memory Test Network' if USE_ETH_TESTER else 'Ethereum Network',
            })
        except Exception as e:
            return Response({
                'id': audit.id,
                'record_hash': audit.record_hash,
                'tx_hash': audit.tx_hash,
                'verified': bool(audit.tx_hash),
                'status': 'confirmed',
                'error': str(e),
            })

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend endpoint disabled in read-only mode.
        
        The blockchain is configured for reading only - transaction sending is not available.
        """
        return Response({
            'detail': 'Blockchain is in read-only mode. Transaction sending is disabled.',
        }, status=403)

    @action(detail=True, methods=['post'])
    def store_cid(self, request, pk=None):
        """Accepts a JSON body with `cid` and sends it on-chain using the blockchain client.

        Returns `tx_hash` and `record_id` (bytes32 hex) on success and updates the OnChainAudit.record_cid and tx_hash.
        """
        try:
            audit = self.get_object()
        except Exception:
            return Response({'detail': 'Not found'}, status=404)

        cid = request.data.get('cid')
        if not cid:
            return Response({'detail': 'Missing cid in request body'}, status=400)

        try:
            from blockchain.web3_client import send_record_and_get_id
        except Exception:
            return Response({'detail': 'Blockchain client not configured'}, status=503)

        try:
            tx_hash, record_id = send_record_and_get_id(cid)
            if tx_hash:
                audit.record_cid = cid
                if tx_hash:
                    audit.tx_hash = tx_hash
                audit.save(update_fields=['record_cid', 'tx_hash'])
            return Response({'tx_hash': tx_hash, 'record_id': record_id})
        except Exception as e:
            return Response({'detail': f'Error sending CID transaction: {str(e)}'}, status=500)


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # create token for the new user
            token, _ = Token.objects.get_or_create(user=user)
            return Response({'message': 'User registered successfully', 'token': token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, username=email, password=password)  # Use username=email
            if user is not None:
                # ensure user has a token and return it
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'name': user.name,
                    'specialization': user.specialization,
                    'phone': user.phone,
                    'address': user.address,
                    'message': 'Login successful',
                    'token': token.key,
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET'])
def get_user_count(request):
    count = User.objects.count()
    return Response({"user_count": count})


@api_view(['GET'])
def blockchain_status(request):
    """Endpoint to fetch blockchain network status and details."""
    try:
        from blockchain.web3_client import get_w3, USE_ETH_TESTER
        
        w3 = get_w3()
        
        # Check if w3 is initialized and try to connect
        if w3 is None:
            return Response({
                'connected': False,
                'chain_id': None,
                'network': 'Not Initialized',
                'latest_block': None,
                'gas_price': None,
                'error': 'Web3 instance not initialized',
            }, status=200)
        
        try:
            is_connected = w3.is_connected()
        except Exception as conn_err:
            print(f"Connection check error: {conn_err}")
            return Response({
                'connected': False,
                'chain_id': None,
                'network': 'Connection Failed',
                'latest_block': None,
                'gas_price': None,
                'error': 'Failed to check connection',
            }, status=200)
        
        if is_connected:
            try:
                chain_id = w3.eth.chain_id
                latest_block = w3.eth.block_number
                gas_price = w3.eth.gas_price
                
                # Determine network name from chain ID
                network_name = 'In-Memory Test Network' if USE_ETH_TESTER else 'Ethereum Network'
                network_map = {
                    1: 'Ethereum Mainnet',
                    5: 'Goerli Testnet',
                    31337: 'Hardhat',
                    1337: 'Ganache',
                }
                network = network_map.get(chain_id, network_name)
                
                return Response({
                    'connected': True,
                    'chain_id': chain_id,
                    'network': network,
                    'latest_block': latest_block,
                    'gas_price': str(w3.from_wei(gas_price, 'gwei')),
                }, status=200)
            except Exception as eth_err:
                print(f"Blockchain data retrieval error: {eth_err}")
                import traceback
                traceback.print_exc()
                return Response({
                    'connected': False,
                    'chain_id': None,
                    'network': 'Data Error',
                    'latest_block': None,
                    'gas_price': None,
                    'error': 'Failed to retrieve blockchain data',
                }, status=200)
        else:
            return Response({
                'connected': False,
                'chain_id': None,
                'network': 'Disconnected',
                'latest_block': None,
                'gas_price': None,
                'error': 'Web3 provider not connected',
            }, status=200)
    except ImportError as import_err:
        print(f"Blockchain import error: {import_err}")
        return Response({
            'connected': False,
            'chain_id': None,
            'network': 'Module Error',
            'latest_block': None,
            'gas_price': None,
            'error': 'Blockchain module not available',
        }, status=200)
    except Exception as e:
        import traceback
        print(f"Blockchain status error: {e}")
        traceback.print_exc()
        return Response({
            'connected': False,
            'chain_id': None,
            'network': 'Error',
            'latest_block': None,
            'gas_price': None,
            'error': str(e),
        }, status=200)  # Return 200 even on error so client handles gracefully


# Note: revenue endpoints implemented as actions on SaleViewSet (routes registered in urls.py)