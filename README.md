# Track Supply of Specific Things in Home Assistant

This integration is for tracking specific items in your household.

- The component is added once for each item (e.g., dishwasher tabs)
- Each item is represented as a service and offers multiple entities
- Supply: How many pieces of the item we have left (entity type `number`)
- Morning/Noon/Evening/Night/Week/Month: How many pieces are regularly consumed (settable in steps of 0.05)?
- Empty: When do we predict the supply to be empty? (sensor of device class `timestamp`). Note that for this purpose, monthly consumption is calculated as per 28 days.
- Soon empty: Do we have to act? (binary sensor of device class `problem`)
- The integration adds two services that can be called regularly (e.g., in the morning) or when specific things happen.
  - The service "consume" reduces the number of items left by the specified amount (this should be run as an automation).
  - The service "store" increases the number of items left. This can be called after groceries have been bought.

## Use Cases

I have developed this integration with two use cases in mind:

- Track medicine for our dog. Unfortunately, [our dog Bona](img/bona.jpeg) is pretty sick, which means we have to regularly feed her several pills. The integration service is called every morning and evening, and we get a prediction on when it is time to get new supplies. ![](img/screenshot1.png)

- Track dishwasher tabs. Every time the dishwasher starts (tracked via power consumption), our supply of dishwasher tabs is reduced by one. To predict when we run out, we assume that we run it 0.5 times every day.

## Installation

This integration is easiest to install via [HACS](https://hacs.xyz). At this moment, you'll have to add `https://github.com/nilsreiter/ha-inventory-manager` as a custom repository though. To do this, follow [this guide](https://hacs.xyz/docs/faq/custom_repositories).

## Description

The integration provides several entities to track the state and supply levels of things. For each thing, the component stores the number of things we have, together with the prescribed use in the morning, at noon, in the evening and at night. Based on this information, the component predicts when we run out -- this is the state of the main sensor. A second "problem sensor" can signal the need to buy new things before we run out (by default, the sensor signals a problem 10 days before we run out).

To make this really useful, the component adds a service call `inventory_manager.consume`, which can be called to signal that a certain amount of things has been consumed. This updates the supply levels of each consumed thing type.

```yaml
service: inventory_manager.consume
data:
  amount: 1
target:
  entity_id: number.dishwasher_tab_supply
```

It is also possible to consume multiple things at once, and for each thing we consume the predefined amount of things (i.e. if 0.5 pills of one type and 1.5 pills of another type has to be taken):

```yaml
service: inventory_manager.consume
data:
  predefined-amount: evening
target:
  entity_id:
    - number.vetmedin_5mg_supply
    - number.vetoryl_30mg_supply
```

