import { expect, test, type Locator } from "@playwright/test";
import { assertAccessibility } from "./accessibility";

async function measureContrast(
  locator: Locator,
  property: "outlineColor" | "borderTopColor",
) {
  return locator.evaluate((element, colorProperty) => {
    const style = getComputedStyle(element);
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    if (!context)
      throw new Error("Canvas indisponible pour mesurer le contraste.");
    function luminance(color: string) {
      if (!context) throw new Error("Canvas indisponible.");
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const rgb = context.getImageData(0, 0, 1, 1).data;
      const linear = [...rgb.slice(0, 3)].map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
    }
    const foreground = luminance(style[colorProperty]);
    const background = luminance(
      getComputedStyle(document.body).backgroundColor,
    );
    return {
      style: style.outlineStyle,
      width: parseFloat(style.outlineWidth),
      offset: parseFloat(style.outlineOffset),
      borderWidth: parseFloat(style.borderTopWidth),
      contrast:
        (Math.max(foreground, background) + 0.05) /
        (Math.min(foreground, background) + 0.05),
    };
  }, property);
}

async function expectVisibleFocus(locator: Locator) {
  await expect(locator).toBeFocused();
  const outline = await measureContrast(locator, "outlineColor");
  expect(outline.style).not.toBe("none");
  expect(outline.width).toBeGreaterThanOrEqual(2);
  expect(outline.offset).toBeGreaterThanOrEqual(2);
  expect(outline.contrast).toBeGreaterThanOrEqual(3);
}

for (const colorScheme of ["light", "dark"] as const) {
  test.describe(`accessibilité en mode ${colorScheme}`, () => {
    test.use({ colorScheme });
    for (const [path, title] of [
      ["/", "Analyse loi vs marché"],
      ["/connexion", "Connexion"],
      ["/connexion?erreur=lien-invalide", "Connexion"],
      ["/inscription", "Créer un compte"],
      ["/mot-de-passe-oublie", "Mot de passe oublié"],
      ["/mentions-legales", "Mentions légales"],
      ["/cgu", "Conditions générales d’utilisation"],
      ["/confidentialite", "Politique de confidentialité"],
    ]) {
      test(`${path} : règles WCAG et contrastes`, async ({ page }) => {
        await page.goto(path);
        await expect(
          page.getByRole("heading", { name: title, exact: true }),
        ).toBeVisible();
        if (path.includes("lien-invalide")) {
          await expect(
            page.getByText(
              "Ce lien est invalide ou a expiré. Veuillez recommencer.",
            ),
          ).toBeVisible();
        }
        await assertAccessibility(page);
      });
    }

    test("accueil : navigation au clavier vers la connexion", async ({
      page,
    }) => {
      await page.goto("/");
      await page.keyboard.press("Tab");
      await expectVisibleFocus(
        page.getByRole("link", { name: "Se connecter" }),
      );
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("heading", { name: "Connexion" }),
      ).toBeVisible();
    });

    test("inscription : parcours du formulaire au clavier", async ({
      page,
    }) => {
      await page.goto("/inscription");
      await expect(page.getByLabel("Nom affiché (facultatif)")).toBeVisible();
      for (const label of [
        "Nom affiché (facultatif)",
        "Adresse e-mail",
        "Mot de passe (10 caractères minimum)",
        "Confirmer le mot de passe",
      ]) {
        await page.keyboard.press("Tab");
        await expectVisibleFocus(page.getByLabel(label));
      }
      await page.keyboard.press("Tab");
      await expectVisibleFocus(
        page.getByRole("button", { name: "S'inscrire" }),
      );
    });

    test("connexion : navigation clavier et erreurs accessibles", async ({
      page,
    }) => {
      await page.goto("/connexion");
      await expect(page.getByLabel("Adresse e-mail")).toBeVisible();
      const border = await measureContrast(
        page.getByLabel("Adresse e-mail"),
        "borderTopColor",
      );
      expect(border.borderWidth).toBeGreaterThanOrEqual(1);
      expect(border.contrast).toBeGreaterThanOrEqual(3);
      await page.keyboard.press("Tab");
      await expectVisibleFocus(page.getByLabel("Adresse e-mail"));
      await page.keyboard.press("Tab");
      await expectVisibleFocus(
        page.getByLabel("Mot de passe", { exact: true }),
      );
      await page.keyboard.press("Tab");
      const submit = page.getByRole("button", { name: "Se connecter" });
      await expectVisibleFocus(submit);
      await page.keyboard.press("Tab");
      await expectVisibleFocus(
        page.getByRole("link", { name: "Mot de passe oublié ?" }),
      );
      await page.keyboard.press("Shift+Tab");
      await expect(submit).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(
        page
          .getByRole("alert")
          .filter({ hasText: "Veuillez corriger les champs en erreur." }),
      ).toBeVisible();
      await expect(page.getByLabel("Adresse e-mail")).toHaveAttribute(
        "aria-invalid",
        "true",
      );
      await expect(
        page.getByLabel("Adresse e-mail"),
      ).toHaveAccessibleDescription("L'adresse e-mail est obligatoire.");
      await assertAccessibility(page);
    });
  });
}
