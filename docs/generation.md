# Generation examples

Run the app using the [quickstart](../README.md#quickstart). These examples
show the supported starting-page scope; model output and public sites can change.

## Try Generate

Start with **Contact form** under Bundled examples for a local example that
works with Demo. **Checkout** is deliberately broken: expecting an order to
succeed demonstrates a failed test and the handoff to Heal.

With LM Studio or Ollama selected, the Generate page also offers these public
practice scenarios. Choose **Use example**, review the populated URL and
scenario, then press **Generate test**. Choosing an example never starts a run.

| Example / target URL | Scenario | Expected check |
| --- | --- | --- |
| **Locked-out account** · [Sauce Demo](https://www.saucedemo.com/) | Attempt to sign in with username locked_out_user and password secret_sauce. Verify the error says Sorry, this user has been locked out. Do not navigate beyond the login page. | The test passes by verifying the account-lockout error. |
| **Customer invoice data** · [The Internet](https://the-internet.herokuapp.com/tables) | In the first data table, find the row for Jason Doe. Verify that his email is `jdoe@hotmail.com` and his amount due is 100 dollars. | The customer's email and amount due match. |
| **Checkbox preferences** · [The Internet](https://the-internet.herokuapp.com/checkboxes) | Check both checkboxes and verify both are checked. Then uncheck both and verify neither is checked. | Both checked and unchecked states are verified. |

These scenarios were generated with `qwen3.6:35b-mlx` on 18 October 2026; each
unedited test passed twice in Chromium. This is a verified starting point, not a
guarantee: external sites and model output can change. Demo does not generate
these public examples. Use **100 dollars**, rather than a currency symbol, in
scenario text: current input validation rejects dollar signs and semicolons.

For example, searching Wikipedia and selecting an article requires later-page
or suggestion-list context that Generate does not collect. A single-page app
can have the same limitation when interactions reveal new controls. Heal can
inspect a failed run's evidence, but it does not turn Generate into an explorer.

## Screenshots

| | |
| --- | --- |
| ![A healed test: the diff, the diagnosis with its confidence and evidence, and the verification result](docs/assets/heal-healed.png) | ![The Model I/O view: the sections sent to the model with their sizes, and the validated reply](docs/assets/heal-model-io.png) |
| **Healed.** The diff, the diagnosis and the proof. | **Model I/O.** What was sent and what came back. |
| ![A heal that stopped: the banner says likely app bug and the test was not changed](docs/assets/heal-app-bug.png) | ![A generated test that passed, with the page context the model was given](docs/assets/generate-passed.png) |
| **Likely app bug.** The test is left alone. | **Generate.** A new spec, run straight away. |
