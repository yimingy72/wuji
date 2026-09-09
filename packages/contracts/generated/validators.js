import * as wujiAjvFormatsModule from 'ajv-formats/dist/formats.js';
const wujiAjvFormats = 'fullFormats' in wujiAjvFormatsModule
  ? wujiAjvFormatsModule
  : wujiAjvFormatsModule.default;
import * as wujiAjvUcs2LengthModule from 'ajv/dist/runtime/ucs2length.js';
const wujiAjvUcs2Length = typeof wujiAjvUcs2LengthModule.default === 'function'
  ? wujiAjvUcs2LengthModule.default
  : wujiAjvUcs2LengthModule.default.default;
"use strict";
export const validateSession = validate21;
const schema32 = {"type":"object","additionalProperties":false,"required":["user_id","display_name","csrf_token","expires_at","permissions_version"],"properties":{"user_id":{"type":"string","format":"uuid"},"display_name":{"type":"string","minLength":1,"maxLength":100},"csrf_token":{"type":"string","minLength":1,"maxLength":256},"expires_at":{"type":"string","format":"date-time"},"permissions_version":{"$ref":"urn:wuji:contracts:0.3#/$defs/Version"}}};
const schema33 = {"type":"integer","minimum":1,"maximum":9007199254740991};
const formats0 = /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const formats2 = wujiAjvFormats.fullFormats["date-time"];
const func1 = wujiAjvUcs2Length;

function validate21(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate21.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.user_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "user_id"},message:"must have required property '"+"user_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.display_name === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "display_name"},message:"must have required property '"+"display_name"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.csrf_token === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "csrf_token"},message:"must have required property '"+"csrf_token"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.expires_at === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "expires_at"},message:"must have required property '"+"expires_at"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.permissions_version === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "permissions_version"},message:"must have required property '"+"permissions_version"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
for(const key0 in data){
if(!(((((key0 === "user_id") || (key0 === "display_name")) || (key0 === "csrf_token")) || (key0 === "expires_at")) || (key0 === "permissions_version"))){
const err5 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.user_id !== undefined){
let data0 = data.user_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err6 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
else {
const err7 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data.display_name !== undefined){
let data1 = data.display_name;
if(typeof data1 === "string"){
if(func1(data1) > 100){
const err8 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/maxLength",keyword:"maxLength",params:{limit: 100},message:"must NOT have more than 100 characters"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(func1(data1) < 1){
const err9 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
else {
const err10 = {instancePath:instancePath+"/display_name",schemaPath:"#/properties/display_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.csrf_token !== undefined){
let data2 = data.csrf_token;
if(typeof data2 === "string"){
if(func1(data2) > 256){
const err11 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/maxLength",keyword:"maxLength",params:{limit: 256},message:"must NOT have more than 256 characters"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(func1(data2) < 1){
const err12 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/csrf_token",schemaPath:"#/properties/csrf_token/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.expires_at !== undefined){
let data3 = data.expires_at;
if(typeof data3 === "string"){
if(!(formats2.validate(data3))){
const err14 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
else {
const err15 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.permissions_version !== undefined){
let data4 = data.permissions_version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err16 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 9007199254740991 || isNaN(data4)){
const err17 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
}
}
else {
const err19 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
validate21.errors = vErrors;
return errors === 0;
}
validate21.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateProject = validate22;
const schema34 = {"type":"object","additionalProperties":false,"required":["id","tenant_id","name","permissions"],"properties":{"id":{"type":"string","format":"uuid"},"tenant_id":{"type":"string","format":"uuid"},"name":{"type":"string","minLength":1,"maxLength":120},"permissions":{"type":"array","maxItems":10,"items":{"$ref":"urn:wuji:contracts:0.3#/$defs/Permission"}}}};
const schema35 = {"type":"string","enum":["project.read","task.preview","task.read","task.create","task.control","artifact.read","artifact.download_sensitive"]};

function validate22(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate22.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.tenant_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.name === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.permissions === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "permissions"},message:"must have required property '"+"permissions"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
for(const key0 in data){
if(!((((key0 === "id") || (key0 === "tenant_id")) || (key0 === "name")) || (key0 === "permissions"))){
const err4 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err5 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
else {
const err6 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err7 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
else {
const err8 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.name !== undefined){
let data2 = data.name;
if(typeof data2 === "string"){
if(func1(data2) > 120){
const err9 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(func1(data2) < 1){
const err10 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
else {
const err11 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.permissions !== undefined){
let data3 = data.permissions;
if(Array.isArray(data3)){
if(data3.length > 10){
const err12 = {instancePath:instancePath+"/permissions",schemaPath:"#/properties/permissions/maxItems",keyword:"maxItems",params:{limit: 10},message:"must NOT have more than 10 items"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(typeof data4 !== "string"){
const err13 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.3#/$defs/Permission/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(!(((((((data4 === "project.read") || (data4 === "task.preview")) || (data4 === "task.read")) || (data4 === "task.create")) || (data4 === "task.control")) || (data4 === "artifact.read")) || (data4 === "artifact.download_sensitive"))){
const err14 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.3#/$defs/Permission/enum",keyword:"enum",params:{allowedValues: schema35.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
}
else {
const err15 = {instancePath:instancePath+"/permissions",schemaPath:"#/properties/permissions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
}
else {
const err16 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
validate22.errors = vErrors;
return errors === 0;
}
validate22.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateProjectPage = validate23;
const schema36 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.3#/$defs/Project"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

function validate23(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate23.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate22(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate22.errors : vErrors.concat(validate22.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if((typeof data2 !== "string") && (data2 !== null)){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/type",keyword:"type",params:{type: schema36.properties.next_cursor.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate23.errors = vErrors;
return errors === 0;
}
validate23.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateApprovedScope = validate25;
const schema37 = {"type":"object","additionalProperties":false,"required":["binding","label","valid_until","origins","allowed_path_prefixes","excluded_path_prefixes","allowed_methods","limits"],"properties":{"binding":{"$ref":"urn:wuji:contracts:0.3#/$defs/ScopeBinding"},"label":{"type":"string","minLength":1,"maxLength":120},"valid_until":{"type":"string","format":"date-time"},"origins":{"type":"array","maxItems":20,"items":{"type":"string","format":"uri","pattern":"^https?://"}},"allowed_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"excluded_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"allowed_methods":{"type":"array","maxItems":2,"items":{"type":"string","enum":["GET","HEAD"]}},"limits":{"$ref":"urn:wuji:contracts:0.3#/$defs/Limits"}}};
const schema40 = {"type":"object","additionalProperties":false,"required":["max_total_requests","requests_per_second","max_concurrent_requests","request_timeout_seconds","max_response_bytes","max_runtime_seconds"],"properties":{"max_total_requests":{"type":"integer","minimum":1,"maximum":200},"requests_per_second":{"type":"number","exclusiveMinimum":0,"maximum":2},"max_concurrent_requests":{"type":"integer","minimum":1,"maximum":2},"request_timeout_seconds":{"type":"integer","minimum":1,"maximum":10},"max_response_bytes":{"type":"integer","minimum":1,"maximum":1048576},"max_runtime_seconds":{"type":"integer","minimum":1,"maximum":600}}};
const schema38 = {"type":"object","additionalProperties":false,"required":["policy_id","version"],"properties":{"policy_id":{"type":"string","format":"uuid"},"version":{"$ref":"urn:wuji:contracts:0.3#/$defs/Version"}}};

function validate26(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate26.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.policy_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "policy_id"},message:"must have required property '"+"policy_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.version === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "policy_id") || (key0 === "version"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.policy_id !== undefined){
let data0 = data.policy_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err3 = {instancePath:instancePath+"/policy_id",schemaPath:"#/properties/policy_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
else {
const err4 = {instancePath:instancePath+"/policy_id",schemaPath:"#/properties/policy_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.version !== undefined){
let data1 = data.version;
if(!(((typeof data1 == "number") && (!(data1 % 1) && !isNaN(data1))) && (isFinite(data1)))){
const err5 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if((typeof data1 == "number") && (isFinite(data1))){
if(data1 > 9007199254740991 || isNaN(data1)){
const err6 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1 < 1 || isNaN(data1)){
const err7 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.3#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate26.errors = vErrors;
return errors === 0;
}
validate26.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const formats12 = wujiAjvFormats.fullFormats.uri;
const pattern4 = new RegExp("^https?://", "u");

function validate25(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate25.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.binding === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "binding"},message:"must have required property '"+"binding"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.label === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "label"},message:"must have required property '"+"label"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.valid_until === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "valid_until"},message:"must have required property '"+"valid_until"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.origins === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "origins"},message:"must have required property '"+"origins"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.allowed_path_prefixes === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_path_prefixes"},message:"must have required property '"+"allowed_path_prefixes"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.excluded_path_prefixes === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "excluded_path_prefixes"},message:"must have required property '"+"excluded_path_prefixes"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.allowed_methods === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_methods"},message:"must have required property '"+"allowed_methods"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.limits === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "limits"},message:"must have required property '"+"limits"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "binding") || (key0 === "label")) || (key0 === "valid_until")) || (key0 === "origins")) || (key0 === "allowed_path_prefixes")) || (key0 === "excluded_path_prefixes")) || (key0 === "allowed_methods")) || (key0 === "limits"))){
const err8 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.binding !== undefined){
if(!(validate26(data.binding, {instancePath:instancePath+"/binding",parentData:data,parentDataProperty:"binding",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
errors = vErrors.length;
}
}
if(data.label !== undefined){
let data1 = data.label;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err9 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(func1(data1) < 1){
const err10 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
else {
const err11 = {instancePath:instancePath+"/label",schemaPath:"#/properties/label/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.valid_until !== undefined){
let data2 = data.valid_until;
if(typeof data2 === "string"){
if(!(formats2.validate(data2))){
const err12 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.origins !== undefined){
let data3 = data.origins;
if(Array.isArray(data3)){
if(data3.length > 20){
const err14 = {instancePath:instancePath+"/origins",schemaPath:"#/properties/origins/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(typeof data4 === "string"){
if(!pattern4.test(data4)){
const err15 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/pattern",keyword:"pattern",params:{pattern: "^https?://"},message:"must match pattern \""+"^https?://"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(!(formats12(data4))){
const err16 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/format",keyword:"format",params:{format: "uri"},message:"must match format \""+"uri"+"\""};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
else {
const err17 = {instancePath:instancePath+"/origins/" + i0,schemaPath:"#/properties/origins/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
}
else {
const err18 = {instancePath:instancePath+"/origins",schemaPath:"#/properties/origins/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.allowed_path_prefixes !== undefined){
let data5 = data.allowed_path_prefixes;
if(Array.isArray(data5)){
if(data5.length > 100){
const err19 = {instancePath:instancePath+"/allowed_path_prefixes",schemaPath:"#/properties/allowed_path_prefixes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
const len1 = data5.length;
for(let i1=0; i1<len1; i1++){
let data6 = data5[i1];
if(typeof data6 === "string"){
if(func1(data6) > 2048){
const err20 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(func1(data6) < 1){
const err21 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
else {
const err22 = {instancePath:instancePath+"/allowed_path_prefixes/" + i1,schemaPath:"#/properties/allowed_path_prefixes/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
}
else {
const err23 = {instancePath:instancePath+"/allowed_path_prefixes",schemaPath:"#/properties/allowed_path_prefixes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.excluded_path_prefixes !== undefined){
let data7 = data.excluded_path_prefixes;
if(Array.isArray(data7)){
if(data7.length > 100){
const err24 = {instancePath:instancePath+"/excluded_path_prefixes",schemaPath:"#/properties/excluded_path_prefixes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
const len2 = data7.length;
for(let i2=0; i2<len2; i2++){
let data8 = data7[i2];
if(typeof data8 === "string"){
if(func1(data8) > 2048){
const err25 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(func1(data8) < 1){
const err26 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
else {
const err27 = {instancePath:instancePath+"/excluded_path_prefixes/" + i2,schemaPath:"#/properties/excluded_path_prefixes/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
}
else {
const err28 = {instancePath:instancePath+"/excluded_path_prefixes",schemaPath:"#/properties/excluded_path_prefixes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.allowed_methods !== undefined){
let data9 = data.allowed_methods;
if(Array.isArray(data9)){
if(data9.length > 2){
const err29 = {instancePath:instancePath+"/allowed_methods",schemaPath:"#/properties/allowed_methods/maxItems",keyword:"maxItems",params:{limit: 2},message:"must NOT have more than 2 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len3 = data9.length;
for(let i3=0; i3<len3; i3++){
let data10 = data9[i3];
if(typeof data10 !== "string"){
const err30 = {instancePath:instancePath+"/allowed_methods/" + i3,schemaPath:"#/properties/allowed_methods/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(!((data10 === "GET") || (data10 === "HEAD"))){
const err31 = {instancePath:instancePath+"/allowed_methods/" + i3,schemaPath:"#/properties/allowed_methods/items/enum",keyword:"enum",params:{allowedValues: schema37.properties.allowed_methods.items.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
}
else {
const err32 = {instancePath:instancePath+"/allowed_methods",schemaPath:"#/properties/allowed_methods/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.limits !== undefined){
let data11 = data.limits;
if(data11 && typeof data11 == "object" && !Array.isArray(data11)){
if(data11.max_total_requests === undefined){
const err33 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if(data11.requests_per_second === undefined){
const err34 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(data11.max_concurrent_requests === undefined){
const err35 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data11.request_timeout_seconds === undefined){
const err36 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
if(data11.max_response_bytes === undefined){
const err37 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(data11.max_runtime_seconds === undefined){
const err38 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
for(const key1 in data11){
if(!((((((key1 === "max_total_requests") || (key1 === "requests_per_second")) || (key1 === "max_concurrent_requests")) || (key1 === "request_timeout_seconds")) || (key1 === "max_response_bytes")) || (key1 === "max_runtime_seconds"))){
const err39 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
if(data11.max_total_requests !== undefined){
let data12 = data11.max_total_requests;
if(!(((typeof data12 == "number") && (!(data12 % 1) && !isNaN(data12))) && (isFinite(data12)))){
const err40 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if((typeof data12 == "number") && (isFinite(data12))){
if(data12 > 200 || isNaN(data12)){
const err41 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data12 < 1 || isNaN(data12)){
const err42 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
}
if(data11.requests_per_second !== undefined){
let data13 = data11.requests_per_second;
if((typeof data13 == "number") && (isFinite(data13))){
if(data13 > 2 || isNaN(data13)){
const err43 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(data13 <= 0 || isNaN(data13)){
const err44 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
}
else {
const err45 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
if(data11.max_concurrent_requests !== undefined){
let data14 = data11.max_concurrent_requests;
if(!(((typeof data14 == "number") && (!(data14 % 1) && !isNaN(data14))) && (isFinite(data14)))){
const err46 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
if((typeof data14 == "number") && (isFinite(data14))){
if(data14 > 2 || isNaN(data14)){
const err47 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if(data14 < 1 || isNaN(data14)){
const err48 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
}
if(data11.request_timeout_seconds !== undefined){
let data15 = data11.request_timeout_seconds;
if(!(((typeof data15 == "number") && (!(data15 % 1) && !isNaN(data15))) && (isFinite(data15)))){
const err49 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
if((typeof data15 == "number") && (isFinite(data15))){
if(data15 > 10 || isNaN(data15)){
const err50 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if(data15 < 1 || isNaN(data15)){
const err51 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
}
if(data11.max_response_bytes !== undefined){
let data16 = data11.max_response_bytes;
if(!(((typeof data16 == "number") && (!(data16 % 1) && !isNaN(data16))) && (isFinite(data16)))){
const err52 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
if((typeof data16 == "number") && (isFinite(data16))){
if(data16 > 1048576 || isNaN(data16)){
const err53 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
if(data16 < 1 || isNaN(data16)){
const err54 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
}
if(data11.max_runtime_seconds !== undefined){
let data17 = data11.max_runtime_seconds;
if(!(((typeof data17 == "number") && (!(data17 % 1) && !isNaN(data17))) && (isFinite(data17)))){
const err55 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
if((typeof data17 == "number") && (isFinite(data17))){
if(data17 > 600 || isNaN(data17)){
const err56 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
if(data17 < 1 || isNaN(data17)){
const err57 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
}
}
}
else {
const err58 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
}
}
else {
const err59 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
validate25.errors = vErrors;
return errors === 0;
}
validate25.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateScopePage = validate28;
const schema41 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.3#/$defs/ApprovedScope"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

function validate28(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate28.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.items === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "items"},message:"must have required property '"+"items"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.next_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "next_cursor"},message:"must have required property '"+"next_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "items") || (key0 === "next_cursor"))){
const err2 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err3 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate25(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate25.errors : vErrors.concat(validate25.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if((typeof data2 !== "string") && (data2 !== null)){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/type",keyword:"type",params:{type: schema41.properties.next_cursor.type},message:"must be string,null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
}
}
else {
const err8 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
validate28.errors = vErrors;
return errors === 0;
}
validate28.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskPreview = validate30;
const schema42 = {"type":"object","additionalProperties":false,"required":["preview_id","project_id","draft","input_digest","effective_scope","expires_at","can_create","blockers"],"properties":{"preview_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"draft":{"$ref":"urn:wuji:contracts:0.3#/$defs/TaskDraft"},"input_digest":{"$ref":"urn:wuji:contracts:0.3#/$defs/Sha256"},"effective_scope":{"$ref":"urn:wuji:contracts:0.3#/$defs/ApprovedScope"},"expires_at":{"type":"string","format":"date-time"},"can_create":{"type":"boolean"},"blockers":{"type":"array","maxItems":20,"items":{"type":"object","additionalProperties":false,"required":["code","message"],"properties":{"code":{"type":"string","enum":["MISSING_ADAPTER","MISSING_IDENTITY","SCOPE_DENIED","AUTHORIZATION_EXPIRED","CREATION_UNAVAILABLE"]},"message":{"type":"string","minLength":1,"maxLength":300}}}}},"allOf":[{"if":{"properties":{"can_create":{"const":true}},"type":"object"},"then":{"properties":{"blockers":{"maxItems":0,"type":"array"}},"type":"object"},"else":{"properties":{"blockers":{"minItems":1,"type":"array"}},"type":"object"}}]};
const schema45 = {"type":"string","pattern":"^[a-f0-9]{64}$"};
const schema43 = {"type":"object","additionalProperties":false,"required":["name","scope","target_url","tool","method","limits"],"properties":{"name":{"type":"string","minLength":1,"maxLength":120},"scope":{"$ref":"urn:wuji:contracts:0.3#/$defs/ScopeBinding"},"target_url":{"type":"string","format":"uri","maxLength":2048,"pattern":"^https?://"},"tool":{"type":"string","const":"http_observe"},"method":{"type":"string","enum":["GET","HEAD"]},"limits":{"$ref":"urn:wuji:contracts:0.3#/$defs/Limits"}}};

function validate31(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate31.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.name === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scope === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scope"},message:"must have required property '"+"scope"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.target_url === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.tool === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tool"},message:"must have required property '"+"tool"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.method === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "method"},message:"must have required property '"+"method"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.limits === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "limits"},message:"must have required property '"+"limits"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
for(const key0 in data){
if(!((((((key0 === "name") || (key0 === "scope")) || (key0 === "target_url")) || (key0 === "tool")) || (key0 === "method")) || (key0 === "limits"))){
const err6 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.name !== undefined){
let data0 = data.name;
if(typeof data0 === "string"){
if(func1(data0) > 120){
const err7 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(func1(data0) < 1){
const err8 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
else {
const err9 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.scope !== undefined){
if(!(validate26(data.scope, {instancePath:instancePath+"/scope",parentData:data,parentDataProperty:"scope",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate26.errors : vErrors.concat(validate26.errors);
errors = vErrors.length;
}
}
if(data.target_url !== undefined){
let data2 = data.target_url;
if(typeof data2 === "string"){
if(func1(data2) > 2048){
const err10 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(!pattern4.test(data2)){
const err11 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/pattern",keyword:"pattern",params:{pattern: "^https?://"},message:"must match pattern \""+"^https?://"+"\""};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(!(formats12(data2))){
const err12 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/format",keyword:"format",params:{format: "uri"},message:"must match format \""+"uri"+"\""};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
else {
const err13 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.tool !== undefined){
let data3 = data.tool;
if(typeof data3 !== "string"){
const err14 = {instancePath:instancePath+"/tool",schemaPath:"#/properties/tool/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if("http_observe" !== data3){
const err15 = {instancePath:instancePath+"/tool",schemaPath:"#/properties/tool/const",keyword:"const",params:{allowedValue: "http_observe"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.method !== undefined){
let data4 = data.method;
if(typeof data4 !== "string"){
const err16 = {instancePath:instancePath+"/method",schemaPath:"#/properties/method/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(!((data4 === "GET") || (data4 === "HEAD"))){
const err17 = {instancePath:instancePath+"/method",schemaPath:"#/properties/method/enum",keyword:"enum",params:{allowedValues: schema43.properties.method.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.limits !== undefined){
let data5 = data.limits;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.max_total_requests === undefined){
const err18 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data5.requests_per_second === undefined){
const err19 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data5.max_concurrent_requests === undefined){
const err20 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data5.request_timeout_seconds === undefined){
const err21 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data5.max_response_bytes === undefined){
const err22 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data5.max_runtime_seconds === undefined){
const err23 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
for(const key1 in data5){
if(!((((((key1 === "max_total_requests") || (key1 === "requests_per_second")) || (key1 === "max_concurrent_requests")) || (key1 === "request_timeout_seconds")) || (key1 === "max_response_bytes")) || (key1 === "max_runtime_seconds"))){
const err24 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data5.max_total_requests !== undefined){
let data6 = data5.max_total_requests;
if(!(((typeof data6 == "number") && (!(data6 % 1) && !isNaN(data6))) && (isFinite(data6)))){
const err25 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if((typeof data6 == "number") && (isFinite(data6))){
if(data6 > 200 || isNaN(data6)){
const err26 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data6 < 1 || isNaN(data6)){
const err27 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
}
if(data5.requests_per_second !== undefined){
let data7 = data5.requests_per_second;
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 > 2 || isNaN(data7)){
const err28 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data7 <= 0 || isNaN(data7)){
const err29 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
else {
const err30 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data5.max_concurrent_requests !== undefined){
let data8 = data5.max_concurrent_requests;
if(!(((typeof data8 == "number") && (!(data8 % 1) && !isNaN(data8))) && (isFinite(data8)))){
const err31 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if((typeof data8 == "number") && (isFinite(data8))){
if(data8 > 2 || isNaN(data8)){
const err32 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
if(data8 < 1 || isNaN(data8)){
const err33 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
}
if(data5.request_timeout_seconds !== undefined){
let data9 = data5.request_timeout_seconds;
if(!(((typeof data9 == "number") && (!(data9 % 1) && !isNaN(data9))) && (isFinite(data9)))){
const err34 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if((typeof data9 == "number") && (isFinite(data9))){
if(data9 > 10 || isNaN(data9)){
const err35 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data9 < 1 || isNaN(data9)){
const err36 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
}
if(data5.max_response_bytes !== undefined){
let data10 = data5.max_response_bytes;
if(!(((typeof data10 == "number") && (!(data10 % 1) && !isNaN(data10))) && (isFinite(data10)))){
const err37 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if((typeof data10 == "number") && (isFinite(data10))){
if(data10 > 1048576 || isNaN(data10)){
const err38 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
if(data10 < 1 || isNaN(data10)){
const err39 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
}
if(data5.max_runtime_seconds !== undefined){
let data11 = data5.max_runtime_seconds;
if(!(((typeof data11 == "number") && (!(data11 % 1) && !isNaN(data11))) && (isFinite(data11)))){
const err40 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if((typeof data11 == "number") && (isFinite(data11))){
if(data11 > 600 || isNaN(data11)){
const err41 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data11 < 1 || isNaN(data11)){
const err42 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
}
}
else {
const err43 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.3#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
}
else {
const err44 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
validate31.errors = vErrors;
return errors === 0;
}
validate31.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const pattern6 = new RegExp("^[a-f0-9]{64}$", "u");

function validate30(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate30.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
const _errs2 = errors;
let valid1 = true;
const _errs3 = errors;
if(errors === _errs3){
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.can_create !== undefined){
if(true !== data.can_create){
const err0 = {};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
}
}
else {
const err1 = {};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
}
var _valid0 = _errs3 === errors;
errors = _errs2;
if(vErrors !== null){
if(_errs2){
vErrors.length = _errs2;
}
else {
vErrors = null;
}
}
let ifClause0;
if(_valid0){
const _errs6 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.blockers !== undefined){
let data1 = data.blockers;
if(Array.isArray(data1)){
if(data1.length > 0){
const err2 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/then/properties/blockers/maxItems",keyword:"maxItems",params:{limit: 0},message:"must NOT have more than 0 items"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
else {
const err3 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/then/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
}
else {
const err4 = {instancePath,schemaPath:"#/allOf/0/then/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
var _valid0 = _errs6 === errors;
valid1 = _valid0;
if(valid1){
var props0 = {};
props0.blockers = true;
props0.can_create = true;
}
ifClause0 = "then";
}
else {
const _errs10 = errors;
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.blockers !== undefined){
let data2 = data.blockers;
if(Array.isArray(data2)){
if(data2.length < 1){
const err5 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/else/properties/blockers/minItems",keyword:"minItems",params:{limit: 1},message:"must NOT have fewer than 1 items"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
else {
const err6 = {instancePath:instancePath+"/blockers",schemaPath:"#/allOf/0/else/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
}
else {
const err7 = {instancePath,schemaPath:"#/allOf/0/else/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = _valid0;
if(valid1){
if(props0 !== true){
props0 = props0 || {};
props0.blockers = true;
}
}
ifClause0 = "else";
}
if(!valid1){
const err8 = {instancePath,schemaPath:"#/allOf/0/if",keyword:"if",params:{failingKeyword: ifClause0},message:"must match \""+ifClause0+"\" schema"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.preview_id === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "preview_id"},message:"must have required property '"+"preview_id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.project_id === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.draft === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "draft"},message:"must have required property '"+"draft"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data.input_digest === undefined){
const err12 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "input_digest"},message:"must have required property '"+"input_digest"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data.effective_scope === undefined){
const err13 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "effective_scope"},message:"must have required property '"+"effective_scope"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data.expires_at === undefined){
const err14 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "expires_at"},message:"must have required property '"+"expires_at"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data.can_create === undefined){
const err15 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "can_create"},message:"must have required property '"+"can_create"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(data.blockers === undefined){
const err16 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "blockers"},message:"must have required property '"+"blockers"+"'"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "preview_id") || (key0 === "project_id")) || (key0 === "draft")) || (key0 === "input_digest")) || (key0 === "effective_scope")) || (key0 === "expires_at")) || (key0 === "can_create")) || (key0 === "blockers"))){
const err17 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.preview_id !== undefined){
let data3 = data.preview_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err18 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
else {
const err19 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err20 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
else {
const err21 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.draft !== undefined){
if(!(validate31(data.draft, {instancePath:instancePath+"/draft",parentData:data,parentDataProperty:"draft",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate31.errors : vErrors.concat(validate31.errors);
errors = vErrors.length;
}
}
if(data.input_digest !== undefined){
let data6 = data.input_digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err22 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.3#/$defs/Sha256/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
else {
const err23 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.3#/$defs/Sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.effective_scope !== undefined){
if(!(validate25(data.effective_scope, {instancePath:instancePath+"/effective_scope",parentData:data,parentDataProperty:"effective_scope",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate25.errors : vErrors.concat(validate25.errors);
errors = vErrors.length;
}
}
if(data.expires_at !== undefined){
let data8 = data.expires_at;
if(typeof data8 === "string"){
if(!(formats2.validate(data8))){
const err24 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
else {
const err25 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data.can_create !== undefined){
if(typeof data.can_create !== "boolean"){
const err26 = {instancePath:instancePath+"/can_create",schemaPath:"#/properties/can_create/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.blockers !== undefined){
let data10 = data.blockers;
if(Array.isArray(data10)){
if(data10.length > 20){
const err27 = {instancePath:instancePath+"/blockers",schemaPath:"#/properties/blockers/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
const len0 = data10.length;
for(let i0=0; i0<len0; i0++){
let data11 = data10[i0];
if(data11 && typeof data11 == "object" && !Array.isArray(data11)){
if(data11.code === undefined){
const err28 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/required",keyword:"required",params:{missingProperty: "code"},message:"must have required property '"+"code"+"'"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data11.message === undefined){
const err29 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
for(const key1 in data11){
if(!((key1 === "code") || (key1 === "message"))){
const err30 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data11.code !== undefined){
let data12 = data11.code;
if(typeof data12 !== "string"){
const err31 = {instancePath:instancePath+"/blockers/" + i0+"/code",schemaPath:"#/properties/blockers/items/properties/code/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if(!(((((data12 === "MISSING_ADAPTER") || (data12 === "MISSING_IDENTITY")) || (data12 === "SCOPE_DENIED")) || (data12 === "AUTHORIZATION_EXPIRED")) || (data12 === "CREATION_UNAVAILABLE"))){
const err32 = {instancePath:instancePath+"/blockers/" + i0+"/code",schemaPath:"#/properties/blockers/items/properties/code/enum",keyword:"enum",params:{allowedValues: schema42.properties.blockers.items.properties.code.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data11.message !== undefined){
let data13 = data11.message;
if(typeof data13 === "string"){
if(func1(data13) > 300){
const err33 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/maxLength",keyword:"maxLength",params:{limit: 300},message:"must NOT have more than 300 characters"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if(func1(data13) < 1){
const err34 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
else {
const err35 = {instancePath:instancePath+"/blockers/" + i0+"/message",schemaPath:"#/properties/blockers/items/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
}
else {
const err36 = {instancePath:instancePath+"/blockers/" + i0,schemaPath:"#/properties/blockers/items/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
}
else {
const err37 = {instancePath:instancePath+"/blockers",schemaPath:"#/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
}
else {
const err38 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
validate30.errors = vErrors;
return errors === 0;
}
validate30.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateError = validate35;
const schema46 = {"type":"object","additionalProperties":false,"required":["code","message","trace_id"],"properties":{"code":{"type":"string","enum":["UNAUTHENTICATED","FORBIDDEN","NOT_FOUND","VALIDATION_FAILED","SCOPE_DENIED","PREVIEW_EXPIRED","VERSION_CONFLICT","IDEMPOTENCY_CONFLICT","INVALID_TRANSITION","RATE_LIMITED","SERVICE_UNAVAILABLE","CURSOR_EXPIRED","INTERNAL_ERROR"]},"message":{"type":"string","minLength":1,"maxLength":500},"trace_id":{"type":"string","format":"uuid"},"field_errors":{"type":"array","maxItems":30,"items":{"type":"object","additionalProperties":false,"required":["field","message"],"properties":{"field":{"type":"string","minLength":1,"maxLength":128},"message":{"type":"string","minLength":1,"maxLength":300}}}}}};

function validate35(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate35.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.code === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "code"},message:"must have required property '"+"code"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.message === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.trace_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "trace_id"},message:"must have required property '"+"trace_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
for(const key0 in data){
if(!((((key0 === "code") || (key0 === "message")) || (key0 === "trace_id")) || (key0 === "field_errors"))){
const err3 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
if(data.code !== undefined){
let data0 = data.code;
if(typeof data0 !== "string"){
const err4 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(!(((((((((((((data0 === "UNAUTHENTICATED") || (data0 === "FORBIDDEN")) || (data0 === "NOT_FOUND")) || (data0 === "VALIDATION_FAILED")) || (data0 === "SCOPE_DENIED")) || (data0 === "PREVIEW_EXPIRED")) || (data0 === "VERSION_CONFLICT")) || (data0 === "IDEMPOTENCY_CONFLICT")) || (data0 === "INVALID_TRANSITION")) || (data0 === "RATE_LIMITED")) || (data0 === "SERVICE_UNAVAILABLE")) || (data0 === "CURSOR_EXPIRED")) || (data0 === "INTERNAL_ERROR"))){
const err5 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/enum",keyword:"enum",params:{allowedValues: schema46.properties.code.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.message !== undefined){
let data1 = data.message;
if(typeof data1 === "string"){
if(func1(data1) > 500){
const err6 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/maxLength",keyword:"maxLength",params:{limit: 500},message:"must NOT have more than 500 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data1) < 1){
const err7 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
else {
const err8 = {instancePath:instancePath+"/message",schemaPath:"#/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.trace_id !== undefined){
let data2 = data.trace_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err9 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
else {
const err10 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.field_errors !== undefined){
let data3 = data.field_errors;
if(Array.isArray(data3)){
if(data3.length > 30){
const err11 = {instancePath:instancePath+"/field_errors",schemaPath:"#/properties/field_errors/maxItems",keyword:"maxItems",params:{limit: 30},message:"must NOT have more than 30 items"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
let data4 = data3[i0];
if(data4 && typeof data4 == "object" && !Array.isArray(data4)){
if(data4.field === undefined){
const err12 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/required",keyword:"required",params:{missingProperty: "field"},message:"must have required property '"+"field"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data4.message === undefined){
const err13 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
for(const key1 in data4){
if(!((key1 === "field") || (key1 === "message"))){
const err14 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data4.field !== undefined){
let data5 = data4.field;
if(typeof data5 === "string"){
if(func1(data5) > 128){
const err15 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/maxLength",keyword:"maxLength",params:{limit: 128},message:"must NOT have more than 128 characters"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(func1(data5) < 1){
const err16 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
else {
const err17 = {instancePath:instancePath+"/field_errors/" + i0+"/field",schemaPath:"#/properties/field_errors/items/properties/field/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data4.message !== undefined){
let data6 = data4.message;
if(typeof data6 === "string"){
if(func1(data6) > 300){
const err18 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/maxLength",keyword:"maxLength",params:{limit: 300},message:"must NOT have more than 300 characters"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(func1(data6) < 1){
const err19 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
else {
const err20 = {instancePath:instancePath+"/field_errors/" + i0+"/message",schemaPath:"#/properties/field_errors/items/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
}
else {
const err21 = {instancePath:instancePath+"/field_errors/" + i0,schemaPath:"#/properties/field_errors/items/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
}
else {
const err22 = {instancePath:instancePath+"/field_errors",schemaPath:"#/properties/field_errors/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
}
else {
const err23 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
validate35.errors = vErrors;
return errors === 0;
}
validate35.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};
