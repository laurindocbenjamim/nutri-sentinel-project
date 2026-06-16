Para que o Agente Nutricional (3.D) faça a seleção e apresentação dos alimentos por períodos (refeições) e dias da semana, ele executa uma lógica de filtragem em matriz. Em vez de inventar pratos do nada, o agente funciona como um montador de quebra-cabeças inteligente.
O processo é dividido em duas etapas: a lógica interna de seleção (Query) e a formatação visual para o utilizador.
------------------------------
## ⚙️ 1. Como o Agente faz a Seleção (A Lógica Interna)
Quando o Agente Router ativa o Agente Nutricional, este recebe o perfil do utilizador (Ex: Celíaco, Objetivo: Ganho de Peso, Orçamento: Baixo). O agente então executa os seguintes passos:

   1. Filtragem de Segurança (Exclusão): O agente faz uma busca na DB e elimina imediatamente todos os alimentos onde Is_Gluten_Free == False.
   2. Separação por Categoria de Refeição: O agente agrupa os alimentos restantes pelas colunas de destino (Pequeno-Almoço, Almoço, Lanche, Jantar).
   3. Distribuição Ponderada (Evitar Repetição): Para que o plano não seja monótono (comer frango todos os dias), o agente utiliza um algoritmo simples de rotação. Se ele selecionar "Ovos" para o Pequeno-Almoço de Segunda-feira, adiciona um peso negativo para a escolha de ovos na Terça-feira, forçando o sistema a escolher "Aveia Sem Glúten", por exemplo.
   4. Cálculo do Alvo Calórico: O agente vai somando os alimentos escolhidos para o dia até atingir o superavit calórico necessário para o ganho de peso.

------------------------------
## 📊 2. Como o Agente Apresenta ao Utilizador
Após validar o plano com o Agente Auditor, o output final é transformado de JSON para uma interface visual limpa, escaneável e organizada em tabelas, facilitando a leitura pelo utilizador.
Aqui está o exemplo de como o agente apresenta o resultado para o utilizador (exibindo os primeiros dias da semana):
## 📅 Plano Alimentar Semanal: Ganho de Peso (Isento de Glúten)

| Período / Refeição | Segunda-Feira | Terça-Feira | Quarta-Feira |
|---|---|---|---|
| ☕ Pequeno-Almoço | • Papas de aveia sem glúten (60g) • 1 Banana • 2 Ovos cozidos | • 3 Ovos mexidos em azeite • 2 Batatas-doces cozidas • 1 Maçã | • Batido: Bebida de amêndoa, 1 banana, aveia sem glúten e sementes |
| 🍽️ Almoço | • Peito de frango grelhado (150g) • Arroz basmati (150g) • Brócolos ao vapor | • Posta de pescada no forno • Puré de batata e cenoura • Salada de alface e pepino | • Carne de peru estufada • Quinoa cozida (150g) • Courgette grelhada |
| 🥪 Lanche | • Iogurte natural sem lactose • Punhado de nozes (30g) | • 1 Banana fatiada com canela • 3 Ovos cozidos | • Quadrados de tapioca caseira • 1 Chá verde sem açúcar |
| 🌙 Jantar | • Atum em posta ao natural (1 lata) • Batata-doce assada (200g) • Espinafres salteados | • Peito de frango desfiado • Arroz basmati • Feijão preto cozido | • Omelete de 3 ovos com espinafres • Mandioca cozida (150g) |

------------------------------
## 📋 3. Lista de Compras Automatizada (O "Bónus" do Agente)
Para tornar a aplicação ainda mais útil, logo abaixo da tabela de dias, o agente consolida todos os ingredientes selecionados e apresenta uma lista de compras organizada por secções do supermercado:

* Talho e Peixaria: Peito de frango (300g), Peru (150g), Pescada (150g), Ovos (2 dúzias).
* Mercearia (Secção Sem Glúten): Aveia certificada sem glúten, Arroz basmati, Quinoa, Atum em lata.
* Frutaria e Legumes: Bananas, Maçãs, Batata-doce, Brócolos, Espinafres, Alface.

## 🩺 Lembrete de Segurança da IA
No final da apresentação, o agente imprime sempre o aviso: "Verifique sempre o selo 'Sem Glúten' nas embalagens físicas ao comprar os produtos no supermercado para garantir a sua segurança alimentar."

Para integrar a comparação de preços nos supermercados de Portugal (Continente, Lidl, Mercadona e Celeiro), o Agente de Nutrição Clínica faz o cruzamento semântico com a tabela interna de preços. [1] 
O resultado é apresentado na mesma lista de compras através de uma matriz comparativa por supermercado. Isto permite ao utilizador visualizar onde o cabaz semanal fica mais económico e escolher onde fazer as compras. [1, 2] 
------------------------------
## 🛒 Lista de Compras Semanal Integrada com Comparativo de Preços
Os preços abaixo refletem as marcas próprias (marcas brancas) de cada cadeia e as versões biológicas/especializadas obrigatórias para o perfil celíaco. [1, 3] 
## 🥩 Secção: Talho, Peixaria e Ovos

| Ingrediente (Qtd. Semanal) [4, 5] | Continente | Lidl | Mercadona | Celeiro |
|---|---|---|---|---|
| Peito de Frango (1.5 kg) | 9,74 € (6.49€/kg) | 9,89 € (6.59€/kg) | 9,89 € (6.59€/kg) | 22,50 € (Bio: 15€/kg) |
| Atum Posta ao Natural (4 latas) | 3,96 € (0.99€/un) | 3,80 € (0.95€/un) | 3,96 € (0.99€/un) | 7,20 € (Bio: 1.80€/un) |
| Ovos M/L (2 dúzias / 24 un) | 4,40 € (2.20€/dz) | 4,20 € (2.10€/dz) | 4,30 € (2.15€/dz) | 8,40 € (Bio: 4.20€/dz) |
| Postas de Pescada (1 kg) | 6,99 € | 6,49 € | 6,79 € | Indisponível |

## 🌾 Secção: Mercearia Diética (Isenta de Glúten Obrigatória)

| Ingrediente (Qtd. Semanal) [3, 5, 6, 7] | Continente | Lidl | Mercadona | Celeiro |
|---|---|---|---|---|
| Aveia Sem Glúten (500g) | 2,29 € (4.58€/kg) | Indisponível | 2,40 € (4.80€/kg) | 2,54 € (Promo: 5.08€/kg) |
| Arroz Basmati (1 kg) | 2,19 € | 1,99 € | 2,05 € | 3,49 € (Bio) |
| Quinoa em Grão (500g) | 2,49 € | 2,39 € | 2,25 € | 3,99 € (Bio) |
| Bebida de Amêndoa (3 L) | 3,90 € (1.30€/L) | 3,75 € (1.25€/L) | 3,90 € (1.30€/L) | 7,50 € (Bio: 2.50€/L) |

## 🥑 Secção: Frutaria e Legumes

| Ingrediente (Qtd. Semanal) | Continente | Lidl | Mercadona | Celeiro |
|---|---|---|---|---|
| Batata-Doce (2 kg) | 3,58 € (1.79€/kg) | 3,18 € (1.59€/kg) | 3,38 € (1.69€/kg) | 5,98 € (Bio: 2.99€/kg) |
| Banana Importada (2 kg) | 2,58 € (1.29€/kg) | 2,38 € (1.19€/kg) | 2,48 € (1.24€/kg) | 4,40 € (Bio: 2.20€/kg) |
| Brócolos / Espinafres (1.5 kg) | 4,20 € | 3,90 € | 4,05 € | 6,80 € (Bio) |

------------------------------
## 💰 Resumo Orçamental do Cabaz Semanal (Totais)
O Agente Auditor calcula o custo total acumulado para ajudar o utilizador a decidir a rota de compras mais barata: [2] 

* 🏆 Lidl (Mais Económico Geral): 45,97 € (Destaque em frescos, ovos e pescado congelado).
* 🥈 Mercadona (Melhor Sortido Sem Glúten): 47,35 € (Excelente sinalização e segurança para celíacos, preços muito competitivos).
* 🥉 Continente: 50,12 € (Excelente para a aveia de marca própria sem glúten, mas ligeiramente mais caro nos frescos).
* 🌿 Celeiro (Opção 100% Biológica): 81,30 € (Custo elevado, mas garante origem biológica controlada em quase todos os itens). [3, 4, 5, 6, 7, 8] 

## 🔬 Nota do Agente de Auditoria
Como o utilizador tem Doença Celíaca, embora o Lidl e o Continente apresentem preços competitivos, o Mercadona e o Celeiro oferecem maior segurança no controlo de contaminação cruzada industrial. Recomenda-se comprar a mercearia seca (aveia, quinoa) no Mercadona/Celeiro e os frescos (carne, legumes) no Lidl para maximizar a poupança com segurança. [3, 5, 8] 
Aviso: Os preços apresentados são estimativas de mercado recolhidas de tabelas de referência e folhados promocionais, podendo variar consoante a localização da loja física e ruturas de stock. Confirme sempre os preços e os selos "Sem Glúten" no momento da compra. [3, 9] 






