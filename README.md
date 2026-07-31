# Yomi — PDI para OCR em scans de mangá com baixa qualidade

O Yomi é um leitor de mangá japonês com OCR e recursos de estudo. O frontend,
a tradução, o dicionário, o furigana e a exportação para Anki são extensões
autorizadas da aplicação; não são apresentados como contribuição de PDI.

## Pergunta acadêmica

> Quando um scan chega com contraste fraco ou ruído, técnicas clássicas de PDI
> conseguem recuperar parte da precisão do OCR?

Em páginas digitais limpas, o OCR funciona normalmente sem PDI. Por isso não
aplicamos mais um pipeline fixo a toda imagem. O experimento reproduz de forma
controlada três problemas encontrados em material de baixa qualidade e escolhe
a técnica correspondente:

| Degradação controlada | Restauração | Laboratório |
|---|---|---|
| baixo contraste | equalização de histograma | Lab 03 |
| ruído gaussiano | filtro Gaussiano 3×3 | Lab 04 |
| ruído sal-e-pimenta | filtro de mediana 3×3 | Lab 04 |

## Fluxo do experimento

```text
Página limpa
   ↓
detector externo (executado uma vez)
   ↓
mesmo recorte e mesma transcrição
   ├── original limpo → OCR
   ├── degradado ─────────────────→ OCR (sem PDI)
   └── degradado → restauração PDI → OCR (com PDI)
```

A degradação acontece depois da localização. Assim, as caixas ficam fixas e a
comparação mede somente o efeito da qualidade dos pixels sobre o OCR.

## O que acontece sem PDI?

O aplicativo continua carregando CBZ, detectando texto, executando OCR,
traduzindo, mostrando furigana/dicionário e exportando Anki. Em material limpo,
isso é inclusive o comportamento recomendado.

Sob degradação, retirar a PDI significa entregar ruído ou baixo contraste
diretamente ao OCR. É nesse cenário que a contribuição se torna mensurável.

## Resultado nas quatro páginas

Foram usadas 52 anotações; 35 foram associadas às caixas fixas do detector.
Menor CER é melhor.

| Cenário | Sem PDI | Com PDI | Redução do CER |
|---|---:|---:|---:|
| baixo contraste | 0,379 | **0,323** | 0,056 |
| ruído gaussiano | 0,360 | **0,269** | 0,091 |
| sal-e-pimenta | 1,335 | **0,273** | 1,062 |

O material original limpo obteve CER 0,257. A restauração não pretende superar
uma entrada perfeita; ela recupera parte do desempenho perdido. As condições
são reproduzidas com parâmetros fixos e intensos, portanto os números
representam um teste de estresse, não a frequência desses defeitos em todo
mangá.

## Por onde começar

Para instalar o projeto em outro computador e preparar a live demo, siga o
[guia completo de setup](docs/SETUP_APRESENTACAO.md).

1. Abra [o notebook](notebooks/01_experimento_pdi.ipynb) e execute em ordem.
2. Leia `backend/pipeline/robustness.py`: são cerca de três degradações e três
   restaurações, sem frontend ou regras de produto.
3. Leia `scripts/evaluate_robustness.py`: mantém as caixas, executa o OCR e
   calcula o CER.
4. Consulte `backend/pipeline/metrics.py` para a definição da métrica.

## Executando o notebook

```bash
cd /Users/matheusmedrado/PDI/yomi
source .venv/bin/activate
python -m pip install -r requirements-notebook.txt
python -m ipykernel install --prefix .venv \
  --name yomi-pdi --display-name "Yomi PDI (Python 3.11)"
python -m jupyterlab notebooks/01_experimento_pdi.ipynb
```

Selecione explicitamente o kernel `Yomi PDI (Python 3.11)`. Não use o Python
3.14 do Homebrew.

Avaliação direta pela linha de comando:

```bash
.venv/bin/python scripts/evaluate_robustness.py
```

Os resultados e as três comparações visuais são gerados em
`presentation_artifacts/robustness/`.

## Demonstração com CBZ limpo e degradado

Dois arquivos curtos, com as mesmas páginas 08–11, ficam prontos na raiz:

- `demo_sample_limpo.cbz` — páginas sem alteração;
- `demo_sample_degradado.cbz` — as mesmas páginas com 10% de ruído
  sal-e-pimenta e sementes fixas.

Eles podem ser recriados de forma determinística com:

```bash
.venv/bin/python scripts/create_degraded_sample.py
```

No leitor, `Sem PDI · original` envia o recorte degradado diretamente ao OCR.
`Com PDI · mediana` aplica `medianBlur` 3×3 ao mesmo recorte antes do OCR. Para
a comparação mais visível, abra a página 03 do CBZ degradado e alterne entre os
dois modos. O teste ao vivo é ilustrativo e degrada a página inteira; os CERs
publicados acima vêm do protocolo controlado, que fixa as caixas do detector.

## Aplicação completa

Backend:

```bash
source .venv/bin/activate
python backend/app.py
```

Frontend, em outro terminal:

```bash
cd frontend
npm run dev
```

`Sem PDI` permanece como padrão para material limpo. O modo de mediana existe
para a demonstração controlada de sal-e-pimenta. Hybrid e PDI-only permanecem
como experimentos anteriores, mas não são a evidência principal do trabalho.

## Verificação

```bash
.venv/bin/python -m pytest -q
cd frontend && npm run build
```
