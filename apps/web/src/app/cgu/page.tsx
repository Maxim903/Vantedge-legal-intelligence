import type { Metadata } from "next";
import { Disclaimer } from "@/components/disclaimer";
import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = {
  title: "Conditions générales d’utilisation",
};

export default function Cgu() {
  return (
    <LegalPage title="Conditions générales d’utilisation">
      <section>
        <h2>Objet et accès au service</h2>
        <p>
          Éditeur : [à renseigner]. Description du service, conditions d’accès,
          offres et modalités d’abonnement : [à compléter].
        </p>
        <p>
          Conditions d’acceptation, date d’effet et modalités de modification
          des CGU : [à définir après validation].
        </p>
      </section>
      <section>
        <h2>Absence de conseil juridique</h2>
        <Disclaimer />
        <p>
          Les résultats sont fournis à titre informatif et ne remplacent pas une
          consultation auprès d’un professionnel du droit. L’utilisateur doit
          vérifier les sources et leur actualité avant toute utilisation.
        </p>
      </section>
      <section>
        <h2>Usages autorisés des données</h2>
        <p>
          L’utilisateur peut consulter les données et résultats dans le cadre de
          l’accès accordé par son offre, sous réserve des droits de tiers, des
          licences applicables et des lois en vigueur.
        </p>
        <p>
          La réutilisation de données publiques est soumise à la licence de la
          source, notamment à ses obligations de citation et de date de mise à
          jour. Les droits d’export, de diffusion, de réutilisation commerciale
          et les éventuelles limites d’extraction automatisée sont à préciser :
          [à compléter].
        </p>
        <p>
          L’utilisateur ne doit pas tenter d’accéder aux données d’autrui sans
          autorisation ni contourner les contrôles d’accès ou les quotas du
          service.
        </p>
      </section>
      <section>
        <h2>Limitation de responsabilité</h2>
        <p>
          Le service peut comporter des erreurs, omissions, retards ou
          indisponibilités. Les exclusions et plafonds de responsabilité
          éventuellement applicables sont à définir par l’éditeur et à valider :
          [à compléter]. Ils ne peuvent écarter les garanties ou responsabilités
          qui ne peuvent être exclues par la loi applicable.
        </p>
      </section>
      <section>
        <h2>Données personnelles et contact</h2>
        <p>
          Les traitements et droits des personnes sont décrits dans la politique
          de confidentialité. Contact, résiliation, droit applicable et
          règlement des différends : [à compléter et valider].
        </p>
      </section>
    </LegalPage>
  );
}
