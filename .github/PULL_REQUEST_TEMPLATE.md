Before: <!-- what a user or developer sees today -->

After: <!-- what they see with this change -->

How: <!-- the approach, briefly; anything a reviewer should look at closely -->

Closes #

## Checklist

- [ ] `make validate` passes, or the `validate-*` target for each package I touched
- [ ] New behavior has a test; a bug fix has a test that fails without it
- [ ] API changes: `make types` run and committed, and `docs/api.md` updated
- [ ] Model changes: migration generated and read
- [ ] New settings documented in `backend/.env.example` and `docs/deployment.md`
- [ ] User-visible change noted in `CHANGELOG.md` under Unreleased
