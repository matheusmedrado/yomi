---
marp: true
theme: default
paginate: true
title: "Yomi — PDI para robustez do OCR de mangá"
description: "Trabalho final de Processamento Digital de Imagens"
style: |
  section { font-family: Arial, sans-serif; color: #171717; padding: 42px; }
  h1, h2 { color: #a61b32; }
  table { font-size: 21px; }
  code { font-size: 18px; }
  .small { font-size: 18px; }
  .note { color: #666; font-size: 16px; }
  .accent { color: #a61b32; font-weight: bold; }
---

# Yomi

## PDI para OCR em scans de mangá com baixa qualidade

**Trabalho Final de Processamento Digital de Imagens**

> Quando um scan perde qualidade, técnicas clássicas de PDI conseguem
> recuperar parte da precisão do OCR?

<div class="note">Frontend, tradução, dicionário, furigana e Anki são extensões
autorizadas da aplicação e não são apresentados como contribuição de PDI.</div>

---

# De onde partimos

O produto já possuía:

```text
Página → detector neural → recorte → OCR neural → recursos de estudo
```

Nossa primeira tentativa aplicava CLAHE, bilateral, Otsu e morfologia em todo
recorte.

**Problema encontrado:** em páginas digitais limpas, o pipeline completo
piorou o CER agregado de **0,257 para 0,277**.

<span class="accent">Decisão:</span> parar de aplicar PDI sem existir uma
degradação que a justifique.

---

# O que acontece sem PDI?

Em uma página limpa, praticamente nada deixa de funcionar:

- detector e caixas continuam;
- OCR continua;
- frontend e recursos de estudo continuam;
- o recorte original é até a melhor entrada.

Logo, a pergunta correta não é “como colocar PDI no sistema?”, mas:

> **Quando existe um defeito de imagem, quanto a técnica adequada consegue
> recuperar?**

---

# Desenho experimental

```text
Página limpa
   ↓ detector executado uma vez
mesma caixa + mesma transcrição
   ├── original limpo → OCR (referência)
   ├── degradado ─────────────────→ OCR (sem PDI)
   └── degradado → restauração PDI → OCR (com PDI)
```

Assim, posição, texto esperado e modelo OCR permanecem iguais. Apenas os pixels
mudam.

---

# Três testes de estresse

| Degradação | Intensidade | Restauração | Conteúdo |
|---|---:|---|---|
| baixo contraste | faixa reduzida a 5% | equalização | Lab 03 |
| ruído gaussiano | σ = 80 | Gaussiano 3×3 | Lab 04 |
| sal-e-pimenta | 10% dos pixels | mediana 3×3 | Lab 04 |

- semente aleatória fixa;
- mesmas quatro páginas;
- mesmos recortes;
- parâmetros iguais em todas as páginas.

<div class="note">As condições foram reproduzidas com parâmetros fixos e
intensos: é um teste controlado de robustez, não uma estimativa de todo mangá
existente.</div>

---

# Baixo contraste → equalização

Comprimimos a faixa dinâmica ao redor da intensidade média:

```text
intensidades espalhadas → intensidades muito próximas
```

A equalização redistribui o histograma para aumentar a separação entre tinta e
papel.

```python
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
restored = cv2.equalizeHist(gray)
```

---

# Evidência: baixo contraste

![width:1050](../presentation_artifacts/robustness/evidence_low_contrast.png)

| Sem PDI | Com equalização |
|---:|---:|
| CER 0,379 | **CER 0,323** |

---

# Ruído gaussiano → filtro Gaussiano

O ruído gaussiano adiciona variações aleatórias de intensidade em toda a
imagem. Aplicamos uma média ponderada que favorece os pixels centrais:

```python
restored = cv2.GaussianBlur(gray, (3, 3), sigmaX=0.9)
```

Trade-off: reduz ruído, mas também pode suavizar traços finos. Por isso usamos
uma máscara pequena.

---

# Evidência: ruído gaussiano

![width:1050](../presentation_artifacts/robustness/evidence_gaussian_noise.png)

| Sem PDI | Com Gaussiano |
|---:|---:|
| CER 0,360 | **CER 0,269** |

---

# Sal-e-pimenta → mediana

Ruído impulsivo substitui pixels por 0 ou 255. A média seria influenciada por
esses extremos; a mediana os descarta quando são minoria na vizinhança.

```python
restored = cv2.medianBlur(gray, 3)
```

Essa é a correspondência mais direta entre tipo de ruído e filtro estudado no
Lab 04.

---

# Evidência: sal-e-pimenta

![width:1050](../presentation_artifacts/robustness/evidence_salt_pepper.png)

| Sem PDI | Com mediana |
|---:|---:|
| CER 1,335 | **CER 0,273** |

---

# Como medimos

Foram preparadas transcrições para 52 regiões nas páginas 08–11.

- 35/52 foram associadas às caixas fixas do detector;
- associação por sobreposição/contenção;
- normalização Unicode NFKC;
- remoção apenas de espaços de leiaute;
- **CER** = distância de Levenshtein / caracteres da referência.

Menor CER significa menos inserções, remoções e substituições de caracteres.

---

# Resultado agregado

| Cenário | Sem PDI | Com PDI | Redução absoluta |
|---|---:|---:|---:|
| baixo contraste | 0,379 | **0,323** | 0,056 |
| ruído gaussiano | 0,360 | **0,269** | 0,091 |
| sal-e-pimenta | 1,335 | **0,273** | 1,062 |

Referência limpa: **CER 0,257**.

> A restauração não supera a imagem perfeita; ela recupera parte do desempenho
> perdido pela degradação.

---

# A conclusão que os dados permitem

- aplicar PDI sempre: **não funcionou**;
- manter a imagem limpa intacta: **melhor decisão**;
- identificar o defeito e escolher a técnica adequada: **reduziu o CER nos
  três testes agregados**;
- maior efeito: mediana sobre ruído sal-e-pimenta.

<span class="accent">Contribuição:</span> um experimento reproduzível que liga
tipo de degradação, técnica clássica de restauração e impacto mensurável no OCR.

---

# Limitações

- condições reproduzidas de forma controlada e intensa;
- apenas quatro páginas e 35 regiões associadas;
- caixas de referência aproximadas;
- teste isola o OCR após a detecção;
- a demonstração de página inteira é ilustrativa, não substitui o protocolo;
- uma técnica pode melhorar o agregado e piorar casos individuais.

Não alegamos precisão geral em qualquer mangá.

---

# Demonstração

1. Notebook: painéis e tabela auditada.
2. Leitor: carregar `demo_sample_limpo.cbz`.
3. Carregar `demo_sample_degradado.cbz` e abrir a página 03.
4. Alternar `Sem PDI · original` e `Com PDI · mediana`.
5. Passar o mouse pelos mesmos balões.

Na página inteira da demo: CER associado **0,387 → 0,161**.

> A tela continua mostrando a página ruidosa. A mediana é aplicada somente ao
> recorte entregue ao OCR.

```bash
.venv/bin/python scripts/create_degraded_sample.py
```

---

# Conclusão

> PDI não é uma etapa obrigatória para uma imagem já limpa. Ela se torna útil
> quando existe uma degradação identificável e escolhemos uma restauração
> compatível.

- baixo contraste → equalização;
- ruído distribuído → Gaussiano;
- ruído impulsivo → mediana;
- em todos os cenários agregados, o CER diminuiu.

## Obrigado — perguntas?

---

# Apêndice — responsabilidades

| Componente | Papel | Contribuição PDI? |
|---|---|---|
| `comic-text-detector` | produz caixas/linhas | não; modelo externo |
| `manga-ocr` | reconhece japonês | não; modelo externo |
| `pipeline/robustness.py` | degrada/restaura pixels | **sim** |
| `evaluate_robustness.py` | protocolo e CER | avaliação |
| frontend/tradução/Anki | aplicação complementar | não |

---

# Apêndice — perguntas esperadas

| Pergunta | Resposta curta |
|---|---|
| “Sem PDI funciona?” | Sim, na imagem limpa. Sob degradação, o CER piora. |
| “Por que degradar artificialmente?” | Para controlar a variável e conhecer a resposta correta. |
| “Por que não usar tudo junto?” | A ablação mostrou que pré-processar sem necessidade pode piorar. |
| “Onde está a matéria?” | Equalização, Gaussiano e mediana, ligados aos Labs 03 e 04. |
| “A rede fez a PDI?” | Não. Detector/OCR ficam fixos; as transformações OpenCV/NumPy são a variável testada. |
| “Isso vale para qualquer mangá?” | Não; é um teste inicial de robustez com limitações declaradas. |
