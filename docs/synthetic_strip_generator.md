# Gerador de Tiras de Urina Sintéticas

## Propósito

Gera imagens sintéticas de tiras reagentes de urina para testar e validar algoritmos de visão computacional (como o Natri Sentinel) sem necessidade de imagens reais.

Cada imagem contém uma tira de plástico branca sobre fundo escuro, com 3 pads coloridos simulando pH, Cetonas e Hidratação. Efeitos realistas podem ser ativados para simular condições de câmara de smartphone.

## Funções

### `gerar_tira_urina_sintetica()`

Gera uma única imagem sintética.

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `caminho_saida` | `str` | `"tira_sintetica.png"` | Caminho para guardar a imagem PNG |
| `largura_cenario` | `int` | `400` | Largura total da imagem (píxeis) |
| `altura_cenario` | `int` | `600` | Altura total da imagem (píxeis) |
| `largura_tira` | `int` | `40` | Largura da tira reagente |
| `altura_tira` | `int` | `400` | Altura da tira reagente |
| `adicionar_sombra` | `bool` | `True` | Aplica gradiente linear preto (10%-20% opacidade) via `cv2.addWeighted` |
| `adicionar_blur` | `bool` | `True` | Aplica `cv2.GaussianBlur` ligeiro (simula câmara fora de foco) |
| `adicionar_rotacao` | `bool` | `True` | Aplica rotação aleatória via `cv2.getRotationMatrix2D` |
| `angulo_max` | `int` | `10` | Ângulo máximo de rotação em graus (ex: 5 ou 10) |

**Retorno:** `dict` com as cores BGR originais de cada pad:
```python
{
    "pH_original_bgr": [120, 190, 230],
    "Cetonas_original_bgr": [200, 220, 240],
    "Hidratacao_original_bgr": [50, 160, 220]
}
```

### `gerar_lote()`

Gera múltiplas imagens de uma só vez.

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `diretorio` | `str` | `"dataset_sintetico"` | Pasta onde as imagens serão guardadas |
| `quantidade` | `int` | `10` | Número de imagens a gerar |
| `**kwargs` | — | — | Qualquer parâmetro da `gerar_tira_urina_sintetica` |

## Efeitos Realistas

### Sombra (Gradiente de Luz)
- Cria um gradiente linear preto (topo→base)
- Blended com a imagem com `cv2.addWeighted`
- Opacidade aleatória entre 10% e 20% em cada imagem
- **Força** o algoritmo de leitura a usar normalização de cor (ex: HSV)

### Desfocagem (Blur)
- `cv2.GaussianBlur(kernel=(3,3), sigma=0.5)`
- Simula câmara de smartphone ligeiramente fora de foco

### Rotação
- `cv2.getRotationMatrix2D` + `cv2.warpAffine`
- Ângulo aleatório entre `-angulo_max` e `+angulo_max`
- **Treina** o algoritmo de alinhamento e correção geométrica antes do recorte dos pads

## Exemplos

```python
# Gerar imagem com todos os efeitos (default)
gerar_tira_urina_sintetica()

# Gerar imagem limpa, sem efeitos
gerar_tira_urina_sintetica(
    adicionar_sombra=False,
    adicionar_blur=False,
    adicionar_rotacao=False,
)

# Gerar lote de 50 imagens com angulo maximo de 5 graus
gerar_lote(quantidade=50, angulo_max=5)

# Gerar lote sem sombra
gerar_lote(quantidade=20, adicionar_sombra=False)
```

## Dependências

```
numpy>=1.24.0
opencv-python>=4.8.0
```
