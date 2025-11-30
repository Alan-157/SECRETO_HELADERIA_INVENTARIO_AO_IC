from rest_framework import serializers
from inventario.models import Insumo, Categoria

class InsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insumo
        fields = '__all__'
        
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
    
    def validate_name(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("El nombre debe tener mínimo 5 caracteres.")
        return value
        
        

