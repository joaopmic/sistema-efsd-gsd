from django import forms


class AjusteForm(forms.Form):
    tipo = forms.ModelChoiceField(label="Nova situação", queryset=None)
    justificativa = forms.CharField(
        label="Justificativa", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, tipos, atual, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].queryset = tipos
        self.fields["tipo"].initial = atual
        self.fields["tipo"].widget.attrs["class"] = "form-select"
        self.fields["justificativa"].widget.attrs["class"] = "form-control"

    def clean(self):
        dados = super().clean()
        return dados
