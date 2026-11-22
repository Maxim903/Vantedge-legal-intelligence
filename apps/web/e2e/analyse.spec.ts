import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import Stripe from "stripe";
import { assertAccessibilityBothThemes } from "./accessibility";

const email = `e2e-${randomUUID()}@example.test`;
const password = `E2e-${randomUUID()}!`;
const project = "Projet synthétique E2E";
const notion = "Notion synthétique E2E";
let stripe: Stripe | undefined;

test.beforeAll(async () => {
  const key = process.env.STRIPE_SECRET_KEY;
  const price = process.env.STRIPE_PRICE_PRO;
  if (!key?.startsWith("sk_test_") || !price?.startsWith("price_")) {
    throw new Error("Une clé Stripe sk_test_ et un prix de test sont requis.");
  }
  const supabase = new URL(process.env.NEXT_PUBLIC_SUPABASE_URL ?? "");
  if (supabase.hostname !== "127.0.0.1" || supabase.port !== "54321") {
    throw new Error("Le test E2E exige une instance Supabase locale dédiée.");
  }
  stripe = new Stripe(key);
  const configuredPrice = await stripe.prices.retrieve(price);
  if (configuredPrice.livemode || !configuredPrice.recurring) {
    throw new Error("Le prix Stripe doit être récurrent et en mode test.");
  }
});

test.afterAll(async () => {
  if (!stripe) return;
  const customers = await stripe.customers.list({ email, limit: 100 });
  if (customers.has_more || customers.data.length > 1) {
    throw new Error("Nettoyage Stripe ambigu : plusieurs clients de test.");
  }
  if (customers.data[0]) await stripe.customers.del(customers.data[0].id);
});

test("inscription, abonnement, ouverture et historique", async ({ page }) => {
  await page.goto("/inscription");
  await page.getByLabel("Adresse e-mail").fill(email);
  await page.getByLabel("Mot de passe (10 caractères minimum)").fill(password);
  await page.getByLabel("Confirmer le mot de passe").fill(password);
  await page.getByRole("button", { name: "S'inscrire" }).click();
  await expect(
    page.getByRole("heading", { name: "Espace connecté" }),
  ).toBeVisible();

  await page.goto("/app/compte/abonnement");
  await expect(
    page.getByRole("button", { name: "Souscrire au plan pro" }),
  ).toBeVisible();
  await assertAccessibilityBothThemes(page);
  await page.getByRole("button", { name: "Souscrire au plan pro" }).click();
  await page.waitForURL(/https:\/\/checkout\.stripe\.com\//);
  await page.getByLabel(/card number|numéro de carte/i).fill("4242424242424242");
  await page
    .getByLabel(/expiration|expiry|date d'expiration/i)
    .fill("1234");
  await page.getByLabel(/security code|cvc|code de sécurité/i).fill("123");
  await page
    .getByLabel(/name on card|nom sur la carte/i)
    .fill("Utilisateur Test");
  const country = page.getByLabel(/country|pays/i);
  if (await country.isVisible()) await country.selectOption("FR");
  const postalCode = page.getByLabel(/postal code|zip code|code postal/i);
  if (await postalCode.isVisible()) await postalCode.fill("75001");
  await page.locator('button[type="submit"]').click();
  await page.waitForURL("**/app/compte?checkout=succes", { timeout: 90_000 });

  const subscription = page
    .getByRole("heading", { name: "Abonnement", exact: true })
    .locator("..");
  await expect
    .poll(
      async () => {
        await page.reload();
        return subscription.innerText();
      },
      { timeout: 60_000, intervals: [1_000, 2_000, 5_000] },
    )
    .toContain("active");

  await page.getByLabel("Nom du nouveau projet").fill(project);
  await page.getByRole("button", { name: "Créer un projet" }).click();
  await expect(page.getByRole("heading", { name: project })).toBeVisible();
  await assertAccessibilityBothThemes(page);
  await page.goto("/app/analyse");
  await expect(page.getByRole("link", { name: notion })).toBeVisible();
  await assertAccessibilityBothThemes(page);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Aller au contenu" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main#contenu")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Situation de vie")).toBeFocused();
  await page.getByRole("link", { name: notion }).click();
  await expect(page.getByLabel("Projet")).toBeVisible();
  await assertAccessibilityBothThemes(page);
  await page.getByLabel("Projet").selectOption({ label: project });
  await page.getByRole("button", { name: "Ouvrir l’analyse" }).click();
  await expect(page.getByRole("heading", { name: notion })).toBeVisible();
  await expect(
    page.getByText("Aucun article source disponible."),
  ).toBeVisible();
  await expect(
    page.getByText("Aucune requête associée disponible."),
  ).toBeVisible();
  await expect(
    page.getByText("Aucun volume mensuel disponible."),
  ).toBeVisible();
  await expect(page.getByText("Aucune intention disponible.")).toBeVisible();
  await expect(page.getByText("Aucun résultat SERP disponible.")).toBeVisible();
  await assertAccessibilityBothThemes(page);

  await page.goto("/app/compte");
  const history = page
    .getByRole("heading", { name: "Historique des analyses" })
    .locator("..");
  await expect(history.getByText(project)).toBeVisible();
  await assertAccessibilityBothThemes(page);
  await expect(
    page.getByText("Consommées ce mois : 1.", { exact: false }),
  ).toBeVisible();
  await history.getByRole("link", { name: "Ouvrir cette analyse" }).click();
  await expect(page.getByRole("heading", { name: notion })).toBeVisible();
  await page.goto("/app/compte");
  await expect(
    page.getByText("Consommées ce mois : 1.", { exact: false }),
  ).toBeVisible();
});
