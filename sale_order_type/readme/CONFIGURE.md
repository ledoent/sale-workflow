To configure Sale Order Types you need to:

1.  Go to **Sales \> Configuration \> Sales Orders Types**
2.  Create a new sale order type with all the settings you want.
3.  *(Optional, developer mode only)* on each type, set the *Precedence*
    field to control how its own pricelist / payment term / warehouse /
    etc. interact with the partner's defaults when a sales order is
    created:

    -   `Sale type wins` — legacy behavior; the type overrides whatever
        the partner derives.
    -   `Partner wins; type fills gaps` — the partner's value is used;
        the type only fills fields the partner leaves empty.
    -   `Ignore type for propagation` — the type's fields are never
        applied to new sales orders; the type acts as a label only.

    The default for newly-created types is set in *Settings \> Sales \>
    Quotations & Orders \> Default precedence for new Sale Order
    Types*. Existing types keep their current value when this default
    changes — upgrading the module preserves legacy behavior
    (`Sale type wins`) for any type that hasn't been touched.
