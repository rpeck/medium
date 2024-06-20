# Example FastAPI REST API

This example REST API illustrates what I consider to be the best practices for building APIs using `FastAPI` and `SQLModel`. `SQLModel` is a rich entity framework built on both `SQLAlchemy` for database persistence and `Pydantic` for serialization and automatic error checking.

We implement a simple CRUD back end for authentication and authorization with general search facility. We have have `Users` and the `Companies` they belong to.

Note that payload fields are not documented with the endpoints, but with the class schemas. These show the datatypes, whether or not fields are optional, etc.

# Endpoints: General

This group of endpoints provide overall status and similar general functionality for the server, e.g. for deployment status checks. In a full REST API, I normally add detailed debugging endpoints here to check and return the status of subsystems such as any databases. These should be protected by authorization and authentication.

## Endpoint: `GET /`

Return a very simple "Hello World" response, as a quick check that the server is up. This does no additional checks.

```json
{"message": "Hello World"}
```

# Endpoints: Users

`User` entities represent the users of this system, whether they are interactive GUI users or direct API users such as a system that is integrated with us via the REST API. Each `User` optionally refers to a `Company` by its unique internal `company_id`.

## Endpoint: `POST /v1/users`

Creates a new User. The endpoint expects a `UserCreate` JSON payload containing the data for the new user, such as:

```json
{   
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@doe.com",
    "company_id": 1000000042,
    "password": "foo!"
}
```

It returns a `UserRead` object.

NOTES: 

* The `email` must be unique across all users in the system.
* If the optional `company_id` is set, the `Company` entity must already exist in the system.

## Endpoint: `GET /v1/users`

Retrieves all available Users, paginated with the `start_with` and `max_count` query parameters. If no Users are not found, it returns an `http` `404` error.

## Endpoint: `GET /v1/users/{id}`

Retrieves a `UserRead` object by its unique ID. If the User is not found, it returns an `http` `404` error.

## Endpoint: `PATCH /v1/users/{id}`

Modifies a User object, changing only the fields that are in the `UserUpdate` payload.

NOTES:
* The `id` field is immutable once the User has been created.
* Use this endpoint to update a User's password.

## Endpoint: `PUT /v1/users/{id}`

Replaces all the fields of a User object except for the `id` with the contents of the `UserUpdate` payload.

NOTES:
* The `id` field is immutable once the User has been created.
* Since all fields are replaced, you probably will want to `GET` the User first and merge in your changes.

## Endpoint: `DELETE /v1/users/{id}`

Deletes the specified User object.

## Endpoint: `POST /v1/users/search`

This endpoint implements a very flexible search mechanism. The simplest type of search is something like:

```json
{
    "type": "User",
    "first_name": "John",
    "last_name": "Doe"
}
```

However, it also lets you send arbitrarily-nested Boolean expressions. 

Let's say we want to find all the Users from company 42 whose last name is not either Smith or Jones. We would write this in Python as:

```python
company_id == 42 and not(last_name == "Smith" or last_name == "Jones")
```

This kind of expression is commonly represented as a kind of tree called an AST ([Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree)). For our API, the payload is composed of `UserSearch` objects to specify field values, combined into a tree with `Not`, `Or` and `And` nodes.

For example, the search expression above would look like this:

[![](https://mermaid.ink/img/pako:eNqdkUFrAjEQhf9KmIsXpVB6WteF1dWDYHvY9tQUGTdjN7BJlmxyEPG_d4yyCL2Zw5AvL7xh5p2hcYogg1-PfSs-q7m0gk_5LaG0SsLPjZfMjTM92tNeK7FYiLdXkR98IfIhHopUvgbyNaFv2h17dvlLUlIdfVbs8-FHrBjfXRh5zdzhEPYWDV27TGqjQzt5ptXmn9fWWRqe8irFbFaI5SNU94ESrO_jJFg9KhuYgiFvUCve8vkqSQgtGZKQ8VXREWPHG5D2wl8xBlefbANZ8JGmEHuFgSqNnI-B7IjdwK-kdHB-d0suBXj5A_V2i70?type=png)](https://mermaid.live/edit#pako:eNqdkUFrAjEQhf9KmIsXpVB6WteF1dWDYHvY9tQUGTdjN7BJlmxyEPG_d4yyCL2Zw5AvL7xh5p2hcYogg1-PfSs-q7m0gk_5LaG0SsLPjZfMjTM92tNeK7FYiLdXkR98IfIhHopUvgbyNaFv2h17dvlLUlIdfVbs8-FHrBjfXRh5zdzhEPYWDV27TGqjQzt5ptXmn9fWWRqe8irFbFaI5SNU94ESrO_jJFg9KhuYgiFvUCve8vkqSQgtGZKQ8VXREWPHG5D2wl8xBlefbANZ8JGmEHuFgSqNnI-B7IjdwK-kdHB-d0suBXj5A_V2i70)

The JSON for this will look like:

```json
{
    "type": "And",
    "children": [
        {
            "type": "User",
            "company_id": 1000000042
        },
        {
            "type": "Not",
            "child": {
                "type": "Or",
                "children": [
                    { "type": "User", "last_name": "Smith" },
                    { "type": "User", "last_name": "Smith" }
                ]
            }
        }
    ]
}
```


# Endpoints: Companies

`Company` entities represent the companies that the Users of this system are associated with. Each `User` optionally refers to a `Company` by its unique internal `company_id`.

## Endpoint: `POST /v1/companies`

Creates a new Company. The endpoint expects a `CompanyCreate` JSON payload containing the data for the new company, such as:

```json
{
	"name": "Acme",
	"address": "1313 Mockingbord Ln"
}
```

It returns a `CompanyRead` object.

## Endpoint: `GET /v1/companies`

Retrieves all available Companies, paginated with the `start_with` and `max_count` query parameters. If no Companies are not found, it returns an `http` `404` error.

## Endpoint: `GET /v1/companies/{id}`

Retrieves a `CompanyRead` object by its unique ID. If the Company is not found, it returns an `http` `404` error.

## Endpoint: `PATCH /v1/companies/{id}`

Modifies a Company object, changing only the fields that are in the `CompanyUpdate` payload, such as:

```json
{
	"name": "Acme International"
}
```

NOTES:
* The `id` field is immutable once the Company has been created.

## Endpoint: `PUT /v1/companies/{id}`

Replaces all the fields of a Company object except for the `id` with the contents of the `CompanyUpdate` payload, e.g.:

```json
{
	"name": "Acme International",
	"address": "1 Acme Drive"
}
```

NOTES:
* The `id` field is immutable once the Company has been created.
* Since all fields are replaced, you probably will want to `GET` the Company first and merge in your changes.

## Endpoint: `DELETE /v1/companies/{id}`

Deletes the specified Company object.

## Endpoint: `POST /v1/companies/search`

This endpoint implements a very flexible search mechanism. See the information on `POST /v1/users/search` for more information. The only difference is the list of fields on which you can search. See the docs for `CompanySearchModel` for details.
