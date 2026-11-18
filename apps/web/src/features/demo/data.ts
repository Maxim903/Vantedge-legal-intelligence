export type DemoNotion = {
  id: string;
  libelle: string;
  definition: string;
  situation: string;
  demande: number;
  saturation: number;
  importance: number;
  ecart: number;
  criticite: number;
  versionScore: string;
  dateCalcul: string;
  articles: { numero: string; titre: string }[];
  requetes: { texte: string; rattachement: number }[];
  volumes: { mois: string; volume: number }[];
  serp: { domaine: string; url: string; position: number }[];
  notionsLiees: string[];
};

export const demoNotions: DemoNotion[] = [
  {
    id: "conges-payes",
    libelle: "Congés payés",
    definition:
      "Droits du salarié à des périodes de repos rémunérées, acquis selon les règles du Code du travail.",
    situation: "Congés et absences",
    demande: 82,
    saturation: 38,
    importance: 76,
    ecart: 50.84,
    criticite: 67,
    versionScore: "demo-v1",
    dateCalcul: "2026-10-01",
    articles: [
      { numero: "L3141-1", titre: "Droit au congé payé annuel" },
      { numero: "L3141-3", titre: "Durée du congé" },
    ],
    requetes: [
      { texte: "calcul congés payés", rattachement: 0.94 },
      { texte: "congés payés et démission", rattachement: 0.82 },
    ],
    volumes: [
      { mois: "Juin", volume: 4200 },
      { mois: "Juil.", volume: 5100 },
      { mois: "Août", volume: 4800 },
      { mois: "Sept.", volume: 3900 },
    ],
    serp: [
      { domaine: "service-public.fr", url: "https://www.service-public.fr/", position: 1 },
      { domaine: "travail-emploi.gouv.fr", url: "https://travail-emploi.gouv.fr/", position: 2 },
    ],
    notionsLiees: ["indemnité de congés payés", "temps de travail"],
  },
  {
    id: "periode-essai",
    libelle: "Période d'essai",
    definition:
      "Période initiale du contrat de travail pendant laquelle sa rupture suit des règles particulières.",
    situation: "Embauche et contrat",
    demande: 65,
    saturation: 54,
    importance: 61,
    ecart: 29.9,
    criticite: 58,
    versionScore: "demo-v1",
    dateCalcul: "2026-10-01",
    articles: [{ numero: "L1221-19", titre: "Durée maximale de la période d'essai" }],
    requetes: [
      { texte: "durée période d'essai", rattachement: 0.91 },
      { texte: "rupture période d'essai délai", rattachement: 0.76 },
    ],
    volumes: [
      { mois: "Juin", volume: 2300 },
      { mois: "Juil.", volume: 2600 },
      { mois: "Août", volume: 2100 },
      { mois: "Sept.", volume: 2800 },
    ],
    serp: [
      { domaine: "service-public.fr", url: "https://www.service-public.fr/", position: 1 },
      { domaine: "code.travail.gouv.fr", url: "https://code.travail.gouv.fr/", position: 3 },
    ],
    notionsLiees: ["contrat de travail", "préavis"],
  },
  {
    id: "demission",
    libelle: "Démission",
    definition:
      "Rupture du contrat de travail à l'initiative du salarié, sous réserve d'une volonté claire et non équivoque.",
    situation: "Fin du contrat",
    demande: 73,
    saturation: 69,
    importance: 72,
    ecart: 22.63,
    criticite: 71,
    versionScore: "demo-v1",
    dateCalcul: "2026-10-01",
    articles: [{ numero: "L1237-1", titre: "Préavis en cas de démission" }],
    requetes: [
      { texte: "démission préavis salarié", rattachement: 0.89 },
      { texte: "démission droits chômage", rattachement: 0.78 },
    ],
    volumes: [
      { mois: "Juin", volume: 3400 },
      { mois: "Juil.", volume: 3100 },
      { mois: "Août", volume: 2900 },
      { mois: "Sept.", volume: 3600 },
    ],
    serp: [
      { domaine: "service-public.fr", url: "https://www.service-public.fr/", position: 1 },
      { domaine: "unedic.org", url: "https://www.unedic.org/", position: 2 },
    ],
    notionsLiees: ["préavis", "rupture conventionnelle"],
  },
];

export const demoSituations = [
  ...new Set(demoNotions.map((notion) => notion.situation)),
];

export function getDemoNotion(id: string): DemoNotion | undefined {
  return demoNotions.find((notion) => notion.id === id);
}
