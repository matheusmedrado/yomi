# Setup do Yomi para a apresentação

Este guia prepara um computador novo para executar o site, o notebook e a
demonstração sem depender de downloads durante a apresentação.

## 1. O que vem pelo GitHub

Depois do commit correto, o repositório deve conter:

- backend e frontend;
- código incorporado de `backend/comic_text_detector`;
- páginas em `sample/`, ground truth, testes e scripts;
- notebook já executado;
- apresentação e roteiros.

Não copie `.venv`, `frontend/node_modules` ou `frontend/dist` de outro
computador. Eles são recriados localmente e podem ser incompatíveis entre
sistemas.

## 2. Arquivos que não vão para o GitHub

Para uma instalação offline e previsível, receba também o arquivo
`yomi_apresentacao_assets.zip`. Ele contém aproximadamente 491 MB e deve ser
extraído **na raiz do repositório**. Depois de extrair, confira esta estrutura:

```text
yomi/
├── local/
│   ├── comictextdetector.pt
│   ├── manga-ocr-base/pytorch_model.bin
│   └── yomi-cache/kanjidic2.json
├── demo_sample_limpo.cbz
├── demo_sample_degradado.cbz
└── presentation_artifacts/robustness/
    ├── results.json
    └── evidence_*.png
```

Os itens realmente indispensáveis para o site são o modelo OCR e
`comictextdetector.pt`. Os CBZs são necessários para a live demo. Os artefatos
de robustez são usados pelos slides e pelo notebook. O cache KANJIDIC é
opcional, mas evita download do dicionário.

Sem o ZIP, o `manga-ocr` tenta baixar seu modelo na primeira utilização. O peso
do detector precisa ser colocado manualmente em `local/comictextdetector.pt`.
Para a apresentação, prefira o ZIP e não dependa da internet.

## 3. Pré-requisitos

- Git;
- Python **3.11** de 64 bits;
- Node.js 20 ou 22;
- aproximadamente 6 GB livres;
- internet durante a instalação das dependências.

Confirme:

```bash
git --version
python3.11 --version
node --version
npm --version
```

No Windows, use `py -3.11 --version` no lugar de `python3.11`.

## 4. Clonar e instalar o Python

```bash
git clone URL_DO_REPOSITORIO
cd yomi
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-notebook.txt
```

Windows PowerShell:

```powershell
git clone URL_DO_REPOSITORIO
cd yomi
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-notebook.txt
```

Sempre use `python -m pip`, nunca apenas `pip`. Isso garante que os pacotes
sejam instalados dentro da `.venv` correta.

## 5. Instalar e compilar o frontend

Na raiz do projeto:

```bash
cd frontend
npm ci
npm run build
cd ..
```

O build permite que o próprio Flask sirva o site, usando apenas um terminal.

## 6. Extrair os arquivos offline

Extraia `yomi_apresentacao_assets.zip` dentro da pasta `yomi`. Não extraia em
uma subpasta adicional. Ao final, deve existir:

```text
local/comictextdetector.pt
local/manga-ocr-base/pytorch_model.bin
demo_sample_degradado.cbz
```

Se recebeu apenas os modelos soltos, copie-os para esses mesmos caminhos.

No macOS ou Linux, também é possível extrair pela raiz do projeto com:

```bash
unzip /caminho/para/yomi_apresentacao_assets.zip
```

No Windows, use “Extrair tudo” e escolha a própria pasta `yomi` como destino.

## 7. Verificar tudo antes da apresentação

Com a `.venv` ativada:

```bash
python scripts/verify_setup.py
python scripts/verify_setup.py --load-models
python -m pytest -q
```

O segundo comando carrega de verdade os dois modelos. Faça isso pelo menos uma
vez antes de sair de casa. O resultado esperado é:

```text
COMPUTADOR PRONTO PARA A APRESENTAÇÃO.
```

## 8. Rodar o site — forma recomendada

Como o frontend já foi compilado, basta:

```bash
source .venv/bin/activate
python backend/app.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python backend/app.py
```

Abra no navegador:

```text
http://127.0.0.1:5001
```

Não feche o terminal. No primeiro upload, espere alguns segundos para os
modelos aquecerem.

### Modo de desenvolvimento, se necessário

Terminal 1:

```bash
source .venv/bin/activate
python backend/app.py
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Nesse caso, abra `http://127.0.0.1:5173`.

## 9. Rodar o notebook

Registre o kernel uma vez:

```bash
source .venv/bin/activate
python -m ipykernel install --user --name yomi-pdi --display-name "Yomi PDI (Python 3.11)"
python -m jupyterlab notebooks/01_experimento_pdi.ipynb
```

No Windows, ative com `.\.venv\Scripts\Activate.ps1`; os demais comandos são
iguais. Selecione o kernel `Yomi PDI (Python 3.11)`.

O notebook já vem com as saídas visuais salvas. Para uma apresentação segura,
mantenha `RECALCULATE = False`. Se usar “Restart Kernel and Run All”, ele
reutilizará `presentation_artifacts/robustness/results.json` e terminará rápido.

## 10. Roteiro da live demo

1. Abra o site antes da sua vez de apresentar.
2. Carregue `demo_sample_limpo.cbz` e mostre `Sem PDI · original`.
3. Volte e carregue `demo_sample_degradado.cbz`.
4. Vá para `03 / 04`.
5. Compare `Sem PDI · original` com `Com PDI · mediana`.
6. No modo de mediana, pressione `D` três vezes para mostrar antes, depois e
   comparação direta; o quarto `D` fecha.
7. Se pedirem técnicas adicionais, selecione `PDI-only · experimental` e use
   `D` para percorrer cinza, HSV, Otsu, morfologia, componentes e watershed.

Consulte também `presentation/GUIA_DEMO_SITE.md`.

## 11. Checklist de contingência

Na véspera ou manhã da apresentação:

- desligue VPN e proxy;
- teste o navegador que será usado;
- execute `python scripts/verify_setup.py --load-models`;
- carregue os dois CBZs uma vez;
- abra a página 03 e percorra toda a tecla `D`;
- abra o notebook e confirme que as imagens já aparecem;
- mantenha `yomi_apresentacao_assets.zip` em um pendrive ou Drive;
- leve também o notebook e os slides em PDF como plano B.

Tradução e download de dicionário podem depender da internet. OCR, detector,
PDI, notebook e live demo funcionam offline quando o pacote de assets foi
extraído corretamente.

## 12. Problemas comuns

### O site abre, mas não aparecem caixas

Confira `local/comictextdetector.pt` e execute:

```bash
python scripts/verify_setup.py --load-models
```

### As caixas aparecem, mas o OCR fica vazio

Confira `local/manga-ocr-base/pytorch_model.bin`.

### O backend abre na porta errada

O projeto usa a porta 5001. Abra `http://127.0.0.1:5001`.

### O frontend mostra uma versão antiga

```bash
cd frontend
npm run build
cd ..
```

Depois faça recarregamento forçado do navegador.

### O PowerShell bloqueia a ativação da `.venv`

Execute apenas na janela atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
