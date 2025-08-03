from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import time
from decimal import Decimal

class Command(BaseCommand):
    help = 'Check database performance and identify optimization opportunities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-queries',
            action='store_true',
            help='Show slow queries from the database',
        )
        parser.add_argument(
            '--check-indexes',
            action='store_true',
            help='Check for missing indexes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting performance check...'))
        
        if options['check_queries']:
            self._check_slow_queries()
        
        if options['check_indexes']:
            self._check_missing_indexes()
        
        self._check_database_stats()

    def _check_slow_queries(self):
        """Check for slow queries if PostgreSQL"""
        self.stdout.write(self.style.WARNING('Checking for slow queries...'))
        
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time
                    FROM pg_stat_statements
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 10;
                """)
                results = cursor.fetchall()
                
                if results:
                    self.stdout.write("Top slow queries:")
                    for query, calls, total_time, mean_time in results:
                        self.stdout.write(f"Mean time: {mean_time:.2f}ms, Calls: {calls}")
                        self.stdout.write(f"Query: {query[:100]}...")
                else:
                    self.stdout.write("No slow queries found or pg_stat_statements not enabled")

    def _check_missing_indexes(self):
        """Check for potentially missing indexes"""
        self.stdout.write(self.style.WARNING('Checking for missing indexes...'))
        
        from customers.models import Customer
        from loans.models import Loan
        
        # Test common queries
        start_time = time.time()
        
        # Query 1: Customer lookup by phone
        Customer.objects.filter(phone_number='1234567890').first()
        query1_time = time.time() - start_time
        
        start_time = time.time()
        # Query 2: Loans by customer and date range
        from datetime import date
        Loan.objects.filter(customer_id=1, end_date__gte=date.today())
        query2_time = time.time() - start_time
        
        self.stdout.write(f"Customer phone lookup: {query1_time*1000:.2f}ms")
        self.stdout.write(f"Loan date filter: {query2_time*1000:.2f}ms")
        
        if query1_time > 0.1:
            self.stdout.write(self.style.ERROR("Phone lookup is slow - check phone_number index"))
        if query2_time > 0.1:
            self.stdout.write(self.style.ERROR("Loan date filter is slow - check composite indexes"))

    def _check_database_stats(self):
        """Show basic database statistics"""
        self.stdout.write(self.style.WARNING('Database statistics:'))
        
        from customers.models import Customer
        from loans.models import Loan
        
        customer_count = Customer.objects.count()
        loan_count = Loan.objects.count()
        
        self.stdout.write(f"Total customers: {customer_count}")
        self.stdout.write(f"Total loans: {loan_count}")
        
        if 'postgresql' in settings.DATABASES['default']['ENGINE']:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables
                    ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;
                """)
                results = cursor.fetchall()
                
                self.stdout.write("\nTable activity:")
                for schema, table, inserts, updates, deletes in results:
                    total_ops = inserts + updates + deletes
                    self.stdout.write(f"{table}: {total_ops} operations (I:{inserts}, U:{updates}, D:{deletes})")

        self.stdout.write(self.style.SUCCESS('Performance check completed!'))