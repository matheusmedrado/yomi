import type { DebugStage, DetectionMode } from "./types";

export interface DebugStageInfo {
  title: string;
  description: string;
  course: string;
}

export const DEBUG_STAGE_INFO: Record<DebugStage, DebugStageInfo> = {
  restoration_original: {
    title: "Sem PDI · recortes originais",
    description: "Pixels do scan enviados diretamente ao OCR, ainda com o ruído.",
    course: "Referência da comparação",
  },
  restoration_filtered: {
    title: "Com PDI · mediana 3×3",
    description: "O mesmo recorte após substituir cada pixel pela mediana da vizinhança 3×3.",
    course: "Lab 04 · filtragem passa-baixa",
  },
  restoration_comparison: {
    title: "Comparação direta",
    description: "Acima estão os recortes sem PDI; abaixo, os mesmos recortes restaurados.",
    course: "Experimento de robustez do OCR",
  },
  gray: {
    title: "1. Escala de cinza",
    description: "Reduz a página a uma intensidade por pixel para simplificar o processamento.",
    course: "Lab 00 · OpenCV",
  },
  mask: {
    title: "2. Máscara de tinta",
    description: "Usa HSV para separar pixels escuros e pouco saturados, candidatos a tinta.",
    course: "Lab 09 · cor",
  },
  otsu: {
    title: "3. Limiar de Otsu",
    description: "Escolhe automaticamente um limiar e produz uma imagem binária de tinta e fundo.",
    course: "Lab 06 · limiarização",
  },
  morphology: {
    title: "4. Morfologia",
    description: "Abertura remove pontos isolados; fechamento une pequenas falhas nos traços.",
    course: "Lab 07 · morfologia matemática",
  },
  cc: {
    title: "5. Componentes conectados",
    description: "Rotula grupos de pixels vizinhos e desenha caixas nos candidatos encontrados.",
    course: "Lab 02 · componentes conexos",
  },
  watershed: {
    title: "6. Watershed",
    description: "Tenta separar componentes de texto que permaneceram encostados.",
    course: "Lab 08 · watershed",
  },
  conditioning_overlay: {
    title: "Visão geral do condicionamento",
    description: "Indica quais caixas usaram PDI, normalização ou fallback no experimento anterior.",
    course: "Pipeline híbrido experimental",
  },
  conditioning_raw: {
    title: "Recorte original",
    description: "Linha extraída pelo detector antes do condicionamento antigo.",
    course: "Referência do pipeline híbrido",
  },
  conditioning_enhanced: {
    title: "Contraste local e redução de ruído",
    description: "Aplica CLAHE e filtro bilateral ao recorte.",
    course: "Labs 03 e 04",
  },
  conditioning_mask: {
    title: "Máscara binária",
    description: "Otsu escolhe a classe de tinta e a morfologia limpa a máscara.",
    course: "Labs 06 e 07",
  },
  conditioning_components: {
    title: "Geometria dos componentes",
    description: "Componentes conectados delimitam a área útil de texto.",
    course: "Lab 02",
  },
  conditioning_projection: {
    title: "Projeção de tinta",
    description: "O perfil horizontal procura espaços com pouca tinta para dividir linhas longas.",
    course: "Análise de projeção",
  },
  conditioning_final: {
    title: "Recortes finais",
    description: "Resultado do condicionamento antigo que seria entregue ao OCR.",
    course: "Pipeline híbrido experimental",
  },
};

const MODE_STAGES: Record<DetectionMode, DebugStage[]> = {
  baseline: ["restoration_original"],
  median_restore: [
    "restoration_original",
    "restoration_filtered",
    "restoration_comparison",
  ],
  hybrid: [
    "conditioning_overlay",
    "conditioning_raw",
    "conditioning_enhanced",
    "conditioning_mask",
    "conditioning_components",
    "conditioning_projection",
    "conditioning_final",
  ],
  pdi_only: ["gray", "mask", "otsu", "morphology", "cc", "watershed"],
};

export function debugStagesFor(mode: DetectionMode): DebugStage[] {
  return MODE_STAGES[mode];
}

export function nextDebugStage(
  mode: DetectionMode,
  current: DebugStage | null,
): DebugStage | null {
  const stages = debugStagesFor(mode);
  if (current === null) return stages[0] ?? null;
  const index = stages.indexOf(current);
  if (index < 0 || index === stages.length - 1) return null;
  return stages[index + 1];
}
