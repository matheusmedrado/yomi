# Roteiro de apresentação — Yomi PDI

## Ideia em uma frase

> Scans de mangá podem chegar com contraste e ruído. Quando identificamos o
> problema, escolhemos uma técnica compatível e medimos quanto do OCR ela
> recupera.

## Fala sugerida (6–8 minutos)

### 1. Contexto — 40 segundos

“O Yomi é um leitor de mangá que eu já desenvolvia, com detector, OCR,
tradução, dicionário e Anki. O professor autorizou manter essas extensões, mas
a contribuição avaliada aqui é somente o processamento de imagem antes do
OCR.”

### 2. A descoberta que mudou o trabalho — 50 segundos

“Nossa primeira tentativa aplicava equalização, filtros, Otsu e morfologia em
todo recorte. Quando medimos, o CER piorou de 0,257 para 0,277. Isso mostrou
que usar muitas técnicas não significa melhorar uma imagem que já está limpa.
Então mudamos a pergunta: quando um scan chega com baixa qualidade, a técnica
apropriada consegue recuperar o OCR?”

### 3. Método — 1 minuto

“O detector é executado uma vez. Depois usamos exatamente as mesmas caixas e
as mesmas transcrições. Um caminho envia a imagem degradada diretamente ao
OCR; o outro restaura a imagem antes do OCR. Dessa forma, localização, texto e
modelo ficam fixos. Só os pixels mudam.”

“Para não comparar páginas ou textos diferentes, reproduzimos no mesmo material
três problemas comuns de baixa qualidade e usamos parâmetros e sementes fixos.
Isso cria um teste de estresse controlado e repetível.”

### 4. Técnicas — 2 minutos

“Para baixo contraste, reduzimos a faixa dinâmica e usamos equalização de
histograma, conteúdo do Lab 03.”

“Para ruído gaussiano, adicionamos ruído distribuído e usamos filtro Gaussiano
3×3. Ele faz uma média ponderada e reduz variações, com o custo de suavizar um
pouco os traços.”

“Para sal-e-pimenta, 10% dos pixels viram preto ou branco. Usamos mediana 3×3,
porque valores extremos não dominam a mediana como dominariam uma média.”

### 5. Resultado — 1 minuto

“Das 52 anotações, 35 foram associadas às caixas fixas. Menor CER é melhor.”

- baixo contraste: 0,379 sem PDI para 0,323 com equalização;
- gaussiano: 0,360 para 0,269;
- sal-e-pimenta: 1,335 para 0,273 com mediana;
- original limpo: 0,257.

“A PDI não supera a imagem perfeita. Ela recupera parte do desempenho que a
degradação retirou.”

### 6. Conclusão — 40 segundos

“Sem PDI, o produto funciona normalmente em imagens limpas. Sob degradação, o
OCR piora. A contribuição é escolher a restauração de acordo com o defeito, e
não aplicar um pipeline fixo em qualquer imagem.”

## Demonstração segura

1. Antes da apresentação, execute:

   ```bash
   cd /Users/matheusmedrado/PDI/yomi
   source .venv/bin/activate
   python -m jupyterlab notebooks/01_experimento_pdi.ipynb
   ```

2. Selecione `Yomi PDI (Python 3.11)`.
3. Deixe `RECALCULATE = False` para a demonstração ser imediata.
4. Execute “Restart Kernel and Run All”.
5. Mostre os três painéis e a tabela. Essa é a evidência quantitativa.

### Demo ao vivo no leitor

1. Deixe backend e frontend abertos antes de começar.
2. Carregue `demo_sample_limpo.cbz` e mostre rapidamente que o OCR funciona no
   modo `Sem PDI · original`.
3. Clique na seta de voltar, no canto superior esquerdo.
4. Carregue `demo_sample_degradado.cbz` e vá para a página **03 / 04**.
5. No seletor superior, mantenha `Sem PDI · original` e passe o mouse pelos
   balões para mostrar o OCR recebendo o ruído.
6. Troque para `Com PDI · mediana` e passe o mouse pelos mesmos balões.
7. Diga: “a página exibida continua degradada; o filtro atua somente no recorte
   encaminhado ao OCR”.

Na validação dessa página inteira, usando as anotações disponíveis, o CER das
regiões associadas caiu de aproximadamente **0,387 para 0,161**. Use esse valor
apenas como apoio da demo; a tabela principal continua sendo o experimento de
caixas fixas do notebook.

Se o tempo estiver curto ou a demo ao vivo falhar, pule direto para os painéis
já gerados no notebook. Eles são a evidência principal e não dependem da rede.

## Perguntas e respostas

### “Sem PDI o sistema funciona?”

Sim. Em imagem limpa, funciona e o original é melhor. A PDI é necessária para
recuperar entradas degradadas nos cenários testados.

### “Por que vocês degradaram a imagem artificialmente?”

Para controlar uma variável por vez, conhecer a causa da perda e repetir o
mesmo ruído com semente fixa. É um teste de robustez.

### “Por que não aplicaram todos os filtros juntos?”

Porque o experimento anterior mostrou que pré-processar sem necessidade pode
piorar o OCR. Cada ruído pede uma técnica diferente.

### “Onde está o conteúdo da matéria?”

Equalização de histograma do Lab 03; filtro Gaussiano e mediana do Lab 04; CER
e protocolo servem para medir o efeito dessas técnicas na aplicação.

### “Detector e OCR são de vocês?”

Não. São modelos externos mantidos fixos. A variável implementada e avaliada é
a restauração clássica com OpenCV e NumPy.

### “Isso funciona em qualquer mangá?”

Não podemos afirmar. São quatro páginas, caixas aproximadas e condições
controladas intensas. O resultado demonstra recuperação nos cenários definidos.

### “Por que só 35 de 52?”

Porque as caixas de referência são aproximadas e o detector não associou todas
com o limiar geométrico usado. Como as caixas são idênticas nos dois caminhos,
isso não favorece PDI nem o Baseline.

## Não dizer

- “PDI sempre melhora OCR.”
- “O projeto detecta texto usando somente PDI.”
- “Os ruídos representam todos os mangás reais.”
- “Nós implementamos o detector ou o manga-ocr.”

## Frase final

> A principal descoberta foi que PDI deve responder a um defeito real da
> imagem. Quando escolhemos a técnica conforme a degradação, o CER diminuiu nos
> três cenários agregados.
