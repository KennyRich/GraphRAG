# Cypher Query Tutorial

## Introduction to Cypher

Cypher is a declarative graph query language that allows for expressive and efficient querying of data in a property graph. It’s designed to be easy to read and write, making it accessible for both developers and non-developers.

## Basic Concepts

- **Node**: An entity in the graph (e.g., a person, place, or event).
- **Relationship**: A connection between two nodes (e.g., "FRIEND", "LIKES").
- **Property**: Attributes or data associated with nodes and relationships.

## Creating Nodes

Nodes are the basic units of data storage in a graph.

```cypher
CREATE (n:Person {name: 'Alice', age: 30, city: 'London'})
CREATE (n:Person {name: 'Bob', age: 25, city: 'Paris'})
```

In this example, we create two nodes with the label `Person` and some properties.

## Creating Relationships

Relationships connect nodes and can also have properties.

```cypher
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:FRIEND {since: 2020}]->(b)
```

This command creates a `FRIEND` relationship from Alice to Bob with a `since` property.

## Basic Queries

### Matching Nodes

To find nodes in the graph, use the `MATCH` keyword.

```cypher
MATCH (n:Person {name: 'Alice'})
RETURN n
```

This query finds the node labeled `Person` with the name `Alice`.

### Retrieving Properties

You can return specific properties of a node.

```cypher
MATCH (n:Person {name: 'Alice'})
RETURN n.name, n.age
```

## Filtering Results

Use the `WHERE` clause to filter results.

```cypher
MATCH (n:Person)
WHERE n.age > 25
RETURN n.name, n.age
```

This query returns the names and ages of people older than 25.

## Advanced Queries

### Pattern Matching

Find nodes based on complex patterns.

```cypher
MATCH (a:Person)-[:FRIEND]->(b:Person)
WHERE a.name = 'Alice'
RETURN b.name
```

This finds all friends of Alice.

### Aggregations

Perform aggregations like counting or averaging.

```cypher
MATCH (n:Person)
RETURN AVG(n.age) AS average_age
```

This query calculates the average age of all people in the graph.

## Modifying Data

### Updating Nodes

Use the `SET` keyword to update properties.

```cypher
MATCH (n:Person {name: 'Alice'})
SET n.age = 31
```

This query updates Alice's age to 31.

### Deleting Nodes and Relationships

To delete nodes or relationships, use the `DELETE` keyword.

```cypher
MATCH (n:Person {name: 'Bob'})
DELETE n
```

This deletes the node labeled `Bob`. If the node has relationships, you must delete them first.

## Combining Queries

You can combine multiple operations using `WITH`.

```cypher
MATCH (a:Person {name: 'Alice'})-[:FRIEND]->(b:Person)
WITH b
MATCH (b)-[:FRIEND]->(c:Person)
RETURN c.name
```

This finds the friends of Alice's friends.

## Example Scenario

Let's put it all together with a more complex example.

1. **Create Nodes**:

    ```cypher
    CREATE (alice:Person {name: 'Alice', age: 30, city: 'London'}),
           (bob:Person {name: 'Bob', age: 25, city: 'Paris'}),
           (carol:Person {name: 'Carol', age: 35, city: 'New York'})
    ```

2. **Create Relationships**:

    ```cypher
    MATCH (alice:Person {name: 'Alice'}), (bob:Person {name: 'Bob'}), (carol:Person {name: 'Carol'})
    CREATE (alice)-[:FRIEND]->(bob),
           (bob)-[:FRIEND]->(carol)
    ```

3. **Query Friends of Friends**:

    ```cypher
    MATCH (alice:Person {name: 'Alice'})-[:FRIEND]->(friend)-[:FRIEND]->(fof)
    RETURN fof.name
    ```

## Conclusion

Cypher is a powerful and expressive language for querying graph databases. This tutorial covered the basics of creating nodes and relationships, querying data, and performing advanced operations. With these fundamentals, you can start exploring and leveraging the power of graph databases for your projects.

Feel free to experiment with these queries and adapt them to your specific needs!
