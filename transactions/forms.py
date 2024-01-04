from django import forms 
from .models import Transaction

# from accounts.models import UserBankAccount

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount','transaction_type']

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account')
        super().__init__(*args, **kwargs)
        self.account = account  
        self.fields['transaction_type'].disabled = True
        self.fields['transaction_type'].widget = forms.HiddenInput()

    def save(self, commit = True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()   
    
class DepositForm(TransactionForm):
    def clean_amount(self):
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount')
        if amount< min_deposit_amount:
            raise forms.ValidationError(
                f"You need to deposit at least {min_deposit_amount}" 
            )
        return amount 

class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance # 1000
        amount = self.cleaned_data.get('amount')
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )
        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )
        if amount > balance: # amount = 5000, tar balance ache 200
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount
    
class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        return amount

class MoneyTransferForm(forms.Form):
    amount = forms.DecimalField()
    to_user_id = forms.IntegerField()

# class MoneyTransferForm(forms.ModelForm):
#     class Meta:
#         model = MoneyTransfer
#         fields = ['sender_account', 'receiver_account', 'amount']

# class MoneyTransferForm(forms.ModelForm):
#     sender_account = forms.ModelChoiceField(queryset=UserBankAccount.objects.all())
#     receiver_account = forms.ModelChoiceField(queryset=UserBankAccount.objects.all())
#     account_number = forms.CharField(label='Account Number') 

#     class Meta:
#         model = Transaction
#         fields = ['sender_account', 'receiver_account', 'account_number', 'amount', 'transaction_type']

#     def clean_amount(self):
#         amount = self.cleaned_data.get('amount')
#         return amount

#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         if commit:
#             instance.save()
#         return instance
    