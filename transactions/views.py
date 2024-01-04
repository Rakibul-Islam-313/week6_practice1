from django.shortcuts import redirect,get_object_or_404,render
from django.views.generic import CreateView, ListView,View
from .forms import MoneyTransferForm
from .import models
from django.contrib.auth.mixins import LoginRequiredMixin 
from .forms import DepositForm, WithdrawForm, LoanRequestForm
from .instance import DEPOSIT, WITHDRAWAL,LOAN,LOAN_PAID,TRANSFER, RECEIVED
from django.db.models import Sum
from transactions.models import Transaction
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime
from django.urls import reverse_lazy
from accounts.models import UserBankAccount
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
# from .forms import MoneyTransferForm
# Create your views here.

# def send_transaction_email(user, amount, subject, template):
#     message = render_to_string(template,{
#         'user': user, 
#         'amount': amount
#     })
#     send_email = EmailMultiAlternatives(subject, '', to=[user.email])
#     send_email.attach_alternative(message, "text/html")
#     send_email.send()

class TransactionCreateMixin(LoginRequiredMixin,CreateView):
    template_name = 'transactions/transaction_form.html'
    model = models.Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs
    
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })
        return context
    
class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        print(self.request.user)
        account = self.request.user.account
        print(account)
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )
        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        return super().form_valid(form)
    
    
class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account

        if not account.is_approved: 
            messages.error(
                self.request,
                'Bank is bankrupt. Withdrawal not approved.'
            )
            return redirect('transaction_report')

        if amount > account.balance:
            # Handle insufficient balance scenario
            messages.error(
                self.request,
                'Insufficient balance to withdraw.'
            )
            return redirect('transaction_report')

        account.balance -= amount
        account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        return super().form_valid(form)
    

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")

        messages.info(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ Pending. Wait for admin approval'
        )
        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
        return queryset.distinct() # unique queryset hote hobe    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')
    
class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    

class MoneyTransferView(View):
    template_name = 'transactions/money_transfer_form.html'
    def get(self,request):
        form = MoneyTransferForm
        return render(request,self.template_name, {'form': form})
    
    def post(self,request):
        form = MoneyTransferForm(request.POST)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            to_user_id = form.cleaned_data['to_user_id']
            print(amount,to_user_id)

            current_user = request.user.account
            # print(current_user)
            try:
                to_user = UserBankAccount.objects.get(account_no = to_user_id)
                # print(to_user)

                current_user.balance-=amount 
                current_user.save()

                to_user.balance+=amount 
                to_user.save()

                Transaction.objects.create(
                    account = current_user,
                    amount = amount,
                    balance_after_transaction = current_user.balance,
                    transaction_type = TRANSFER 
                )

                Transaction.objects.create(
                    account = to_user,
                    amount = amount,
                    balance_after_transaction = to_user.balance,
                    transaction_type = RECEIVED 
                )

                messages.success(request, "Successfully transferred")
                return redirect('transaction_report')
            
            except UserBankAccount.DoesNotExist:
                messages.error(request,"User Account does not exist")
            return render(request,self.template_name, {'form': form, 'title': 'transaction_report'})
        return render(request, self.template_name, {'form': form, 'title': 'Transfer Money'})
       
    
