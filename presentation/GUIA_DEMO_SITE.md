# Guia da demonstração ao vivo do Yomi

## Respostas curtas para a banca

### O PDI está alinhado aos laboratórios?

Sim. As três técnicas que sustentam o resultado principal vêm diretamente dos
Labs 03 e 04:

| Projeto | Laboratório | Relação |
|---|---|---|
| `cv2.equalizeHist` | Lab 03 | é a mesma equalização global usada no notebook do laboratório |
| `cv2.GaussianBlur` 3×3 | Lab 04 | é a aplicação otimizada do mesmo kernel Gaussiano construído e convoluído no lab |
| `cv2.medianBlur` 3×3 | Lab 04 | é o mesmo filtro de mediana aplicado manualmente ao ruído sal-e-pimenta |

O projeto usa as funções otimizadas do OpenCV porque a ideia matemática já foi
implementada e estudada manualmente nos labs. A aplicação mudou; a operação de
PDI é a mesma.

O modo `PDI-only · experimental` ainda permite visualizar conteúdos adicionais:

| Tela | Conteúdo |
|---|---|
| escala de cinza | Lab 00 |
| máscara HSV | Lab 09 |
| limiar de Otsu | Lab 06 |
| abertura e fechamento | Lab 07 |
| componentes conectados | Lab 02 |
| watershed | Lab 08 |

Esses estágios adicionais são uma exploração de localização clássica. Eles não
são a evidência quantitativa principal, que é equalização/Gaussiano/mediana
antes do OCR.

### Quem decide aplicar PDI?

Na versão apresentada, **o usuário decide pelo seletor**:

- `Sem PDI · original`: comportamento padrão para material limpo;
- `Com PDI · mediana`: opção para scan com ruído impulsivo sal-e-pimenta.

O sistema não classifica automaticamente o defeito. Isso é deliberado: aplicar
o filtro errado em uma página limpa pode piorar o OCR, como a primeira avaliação
do projeto mostrou (`CER 0,257 → 0,277`). Uma decisão automática exigiria um
classificador de qualidade validado, que fica como trabalho futuro.

Se perguntarem como automatizar, a resposta é: medir faixa dinâmica do
histograma para contraste, frequência de pixels extremos isolados para
sal-e-pimenta e energia de alta frequência para ruído distribuído; só então
selecionar a restauração. **Isso ainda não está implementado.**

## Demonstração principal: mediana

1. Carregue `demo_sample_degradado.cbz`.
2. Vá para a página `03 / 04`.
3. Deixe `Sem PDI · original` e passe o mouse em alguns balões.
4. Troque para `Com PDI · mediana` e repita nos mesmos balões.
5. Pressione `D` três vezes:

   1. **Sem PDI:** recortes com os pontos do ruído;
   2. **Com PDI:** os mesmos recortes após mediana 3×3;
   3. **Comparação direta:** antes em cima, depois embaixo.

6. Pressione `D` mais uma vez para fechar.

Fala sugerida:

> O usuário identificou ruído impulsivo e selecionou a mediana. A localização
> das caixas não muda entre os dois caminhos; muda somente o recorte entregue
> ao OCR. Cada pixel passa a receber a mediana de sua vizinhança 3×3, removendo
> valores extremos sem borrar os contornos tanto quanto uma média.

## Demonstração opcional: conteúdos da disciplina

Se o professor quiser ver mais etapas, selecione `PDI-only · experimental` e
pressione `D` repetidamente:

1. **Escala de cinza:** reduz BGR a uma intensidade por pixel.
2. **Máscara de tinta:** usa HSV para manter pixels escuros e pouco saturados.
3. **Otsu:** calcula automaticamente o limiar entre tinta e fundo.
4. **Morfologia:** abertura remove pontos; fechamento liga pequenas falhas.
5. **Componentes conectados:** rotula conjuntos vizinhos e desenha caixas.
6. **Watershed:** tenta separar componentes que continuam encostados.
7. O próximo `D` fecha a explicação.

Cada tela agora mostra seu nome, explicação e laboratório correspondente no
rodapé. O ciclo do botão com ícone de lupa é exatamente o mesmo da tecla `D`.

## O que não dizer

- Não diga que o app detecta sozinho qual filtro usar.
- Não diga que Otsu, componentes e watershed geram as caixas do modo padrão;
  nele as caixas vêm do detector externo.
- Não diga que PDI sempre melhora. Ela melhora o agregado nos defeitos testados.
- Não apresente Hybrid ou PDI-only como resultado principal; são modos
  experimentais e de inspeção.
