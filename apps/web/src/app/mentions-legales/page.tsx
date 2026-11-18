import type { Metadata } from "next";
import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = { title: "Mentions légales" };

export default function MentionsLegales() {
  return (
    <LegalPage title="Mentions légales">
      <section>
        <h2>Éditeur du service</h2>
        <p>
          Nom ou dénomination : [à renseigner]. Forme juridique, capital le cas
          échéant, numéro d’immatriculation et TVA : [à renseigner selon le
          cas].
        </p>
        <p>
          Adresse du siège ou de l’établissement, adresse électronique et
          téléphone : [à renseigner].
        </p>
        <p>Directeur ou responsable de la publication : [à renseigner].</p>
      </section>
      <section>
        <h2>Hébergement</h2>
        <p>Hébergeur, adresse et coordonnées : [à renseigner et vérifier].</p>
      </section>
      <section>
        <h2>Sources des données juridiques</h2>
        <p>
          Sources effectivement utilisées, références des jeux de données,
          licences applicables et dates de mise à jour des données : [à
          renseigner et maintenir à jour].
        </p>
        <p>
          Pour les contenus relevant de la Licence Ouverte, vérifier et afficher
          les mentions de source et les dates requises avant publication.
        </p>
      </section>
      <section>
        <h2>Contact</h2>
        <p>Contact pour toute question relative au service : [à renseigner].</p>
      </section>
    </LegalPage>
  );
}
