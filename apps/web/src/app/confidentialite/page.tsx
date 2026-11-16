import type { Metadata } from "next";
import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = { title: "Politique de confidentialité" };

export default function Confidentialite() {
  return (
    <LegalPage title="Politique de confidentialité">
      <section>
        <h2>Responsable et contact</h2>
        <p>
          Responsable du traitement, coordonnées et contact pour les demandes
          relatives aux données personnelles : [à renseigner]. Délégué à la
          protection des données, le cas échéant : [à renseigner].
        </p>
      </section>
      <section>
        <h2>Données et finalités</h2>
        <p>
          À vérifier et compléter pour chaque traitement : données de compte et
          de profil, projets et analyses, données d’abonnement et de
          facturation, journaux techniques et éventuelles données de navigation.
        </p>
        <p>
          Finalités, bases légales, caractère obligatoire ou facultatif des
          données et conséquences d’un défaut de fourniture : [à renseigner pour
          chaque traitement].
        </p>
      </section>
      <section>
        <h2>Durées de conservation</h2>
        <p>
          Durées ou critères de détermination, y compris pour les comptes,
          projets, analyses, données de facturation et journaux : [à renseigner
          pour chaque catégorie].
        </p>
      </section>
      <section>
        <h2>Destinataires et transferts</h2>
        <p>
          Destinataires et sous-traitants effectivement utilisés, rôles, données
          transmises et finalités : [à inventorier]. Pays de traitement,
          éventuels transferts hors de l’UE/EEE et garanties applicables : [à
          vérifier et renseigner].
        </p>
      </section>
      <section>
        <h2>Droits des personnes</h2>
        <p>
          Dans les conditions prévues par la réglementation applicable, les
          personnes peuvent notamment demander l’accès, la rectification ou la
          suppression de leurs données, ainsi que leur portabilité lorsque
          celle-ci s’applique. Modalités pour exercer ces droits, délais et
          possibilité de réclamation auprès de l’autorité compétente : [à
          compléter].
        </p>
      </section>
      <section>
        <h2>Cookies et sécurité</h2>
        <p>
          Cookies ou technologies similaires, finalités, durées et choix
          proposés ; mesures de sécurité pertinentes : [à inventorier et
          compléter].
        </p>
      </section>
    </LegalPage>
  );
}
