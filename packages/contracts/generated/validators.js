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
const schema32 = {"type":"object","additionalProperties":false,"required":["user_id","display_name","csrf_token","expires_at","permissions_version"],"properties":{"user_id":{"type":"string","format":"uuid"},"display_name":{"type":"string","minLength":1,"maxLength":100},"csrf_token":{"type":"string","minLength":1,"maxLength":256},"expires_at":{"type":"string","format":"date-time"},"permissions_version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"}}};
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
const err16 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err17 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/permissions_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const schema34 = {"type":"object","additionalProperties":false,"required":["id","tenant_id","name","permissions"],"properties":{"id":{"type":"string","format":"uuid"},"tenant_id":{"type":"string","format":"uuid"},"name":{"type":"string","minLength":1,"maxLength":120},"permissions":{"type":"array","maxItems":10,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Permission"}}}};
const schema35 = {"type":"string","enum":["project.read","model.profile.read","task.draft.read","task.draft.write","task.preview","task.read","task.create","task.control","artifact.read","artifact.download_sensitive"]};

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
const err13 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Permission/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(!((((((((((data4 === "project.read") || (data4 === "model.profile.read")) || (data4 === "task.draft.read")) || (data4 === "task.draft.write")) || (data4 === "task.preview")) || (data4 === "task.read")) || (data4 === "task.create")) || (data4 === "task.control")) || (data4 === "artifact.read")) || (data4 === "artifact.download_sensitive"))){
const err14 = {instancePath:instancePath+"/permissions/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Permission/enum",keyword:"enum",params:{allowedValues: schema35.enum},message:"must be equal to one of the allowed values"};
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
const schema36 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Project"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

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
const schema37 = {"type":"object","additionalProperties":false,"required":["binding","label","valid_until","origins","allowed_path_prefixes","excluded_path_prefixes","allowed_methods","limits"],"properties":{"binding":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBinding"},"label":{"type":"string","minLength":1,"maxLength":120},"valid_until":{"type":"string","format":"date-time"},"origins":{"type":"array","maxItems":20,"items":{"type":"string","format":"uri","pattern":"^https?://"}},"allowed_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"excluded_path_prefixes":{"type":"array","maxItems":100,"items":{"type":"string","minLength":1,"maxLength":2048}},"allowed_methods":{"type":"array","maxItems":2,"items":{"type":"string","enum":["GET","HEAD"]}},"limits":{"$ref":"urn:wuji:contracts:0.5#/$defs/Limits"}}};
const schema40 = {"type":"object","additionalProperties":false,"required":["max_total_requests","requests_per_second","max_concurrent_requests","request_timeout_seconds","max_response_bytes","max_runtime_seconds"],"properties":{"max_total_requests":{"type":"integer","minimum":1,"maximum":200},"requests_per_second":{"type":"number","exclusiveMinimum":0,"maximum":2},"max_concurrent_requests":{"type":"integer","minimum":1,"maximum":2},"request_timeout_seconds":{"type":"integer","minimum":1,"maximum":10},"max_response_bytes":{"type":"integer","minimum":1,"maximum":1048576},"max_runtime_seconds":{"type":"integer","minimum":1,"maximum":600}}};
const schema38 = {"type":"object","additionalProperties":false,"required":["policy_id","version"],"properties":{"policy_id":{"type":"string","format":"uuid"},"version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"}}};

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
const err5 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err6 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1 < 1 || isNaN(data1)){
const err7 = {instancePath:instancePath+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err33 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if(data11.requests_per_second === undefined){
const err34 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(data11.max_concurrent_requests === undefined){
const err35 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data11.request_timeout_seconds === undefined){
const err36 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
if(data11.max_response_bytes === undefined){
const err37 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(data11.max_runtime_seconds === undefined){
const err38 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
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
const err39 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
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
const err40 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err41 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data12 < 1 || isNaN(data12)){
const err42 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err43 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(data13 <= 0 || isNaN(data13)){
const err44 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
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
const err45 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
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
const err46 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err47 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if(data14 < 1 || isNaN(data14)){
const err48 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err49 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err50 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if(data15 < 1 || isNaN(data15)){
const err51 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err52 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err53 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
if(data16 < 1 || isNaN(data16)){
const err54 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err55 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err56 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
if(data17 < 1 || isNaN(data17)){
const err57 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err58 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
const schema41 = {"type":"object","additionalProperties":false,"required":["items","next_cursor"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ApprovedScope"}},"next_cursor":{"type":["string","null"],"minLength":1,"maxLength":512}}};

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
const schema42 = {"type":"object","additionalProperties":false,"required":["preview_id","project_id","draft","input_digest","effective_scope","expires_at","can_create","blockers"],"properties":{"preview_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"draft":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskDraft"},"input_digest":{"$ref":"urn:wuji:contracts:0.5#/$defs/Sha256"},"effective_scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ApprovedScope"},"expires_at":{"type":"string","format":"date-time"},"can_create":{"type":"boolean"},"blockers":{"type":"array","maxItems":20,"items":{"type":"object","additionalProperties":false,"required":["code","message"],"properties":{"code":{"type":"string","enum":["MISSING_ADAPTER","MISSING_IDENTITY","SCOPE_DENIED","AUTHORIZATION_EXPIRED","CREATION_UNAVAILABLE"]},"message":{"type":"string","minLength":1,"maxLength":300}}}}},"allOf":[{"if":{"properties":{"can_create":{"const":true}},"type":"object"},"then":{"properties":{"blockers":{"maxItems":0,"type":"array"}},"type":"object"},"else":{"properties":{"blockers":{"minItems":1,"type":"array"}},"type":"object"}}]};
const schema45 = {"type":"string","pattern":"^[a-f0-9]{64}$"};
const schema43 = {"type":"object","additionalProperties":false,"required":["name","scope","target_url","tool","method","limits"],"properties":{"name":{"type":"string","minLength":1,"maxLength":120},"scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBinding"},"target_url":{"type":"string","format":"uri","maxLength":2048,"pattern":"^https?://"},"tool":{"type":"string","const":"http_observe"},"method":{"type":"string","enum":["GET","HEAD"]},"limits":{"$ref":"urn:wuji:contracts:0.5#/$defs/Limits"}}};

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
const err18 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_total_requests"},message:"must have required property '"+"max_total_requests"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data5.requests_per_second === undefined){
const err19 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "requests_per_second"},message:"must have required property '"+"requests_per_second"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data5.max_concurrent_requests === undefined){
const err20 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_concurrent_requests"},message:"must have required property '"+"max_concurrent_requests"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data5.request_timeout_seconds === undefined){
const err21 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "request_timeout_seconds"},message:"must have required property '"+"request_timeout_seconds"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data5.max_response_bytes === undefined){
const err22 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_response_bytes"},message:"must have required property '"+"max_response_bytes"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data5.max_runtime_seconds === undefined){
const err23 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/required",keyword:"required",params:{missingProperty: "max_runtime_seconds"},message:"must have required property '"+"max_runtime_seconds"+"'"};
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
const err24 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
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
const err25 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err26 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 200},message:"must be <= 200"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data6 < 1 || isNaN(data6)){
const err27 = {instancePath:instancePath+"/limits/max_total_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_total_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err28 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data7 <= 0 || isNaN(data7)){
const err29 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/exclusiveMinimum",keyword:"exclusiveMinimum",params:{comparison: ">", limit: 0},message:"must be > 0"};
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
const err30 = {instancePath:instancePath+"/limits/requests_per_second",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/requests_per_second/type",keyword:"type",params:{type: "number"},message:"must be number"};
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
const err31 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err32 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/maximum",keyword:"maximum",params:{comparison: "<=", limit: 2},message:"must be <= 2"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
if(data8 < 1 || isNaN(data8)){
const err33 = {instancePath:instancePath+"/limits/max_concurrent_requests",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_concurrent_requests/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err34 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err35 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 10},message:"must be <= 10"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data9 < 1 || isNaN(data9)){
const err36 = {instancePath:instancePath+"/limits/request_timeout_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/request_timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err37 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err38 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
if(data10 < 1 || isNaN(data10)){
const err39 = {instancePath:instancePath+"/limits/max_response_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_response_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err40 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
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
const err41 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 600},message:"must be <= 600"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(data11 < 1 || isNaN(data11)){
const err42 = {instancePath:instancePath+"/limits/max_runtime_seconds",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/properties/max_runtime_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
const err43 = {instancePath:instancePath+"/limits",schemaPath:"urn:wuji:contracts:0.5#/$defs/Limits/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
const err22 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err23 = {instancePath:instancePath+"/input_digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/Sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
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

export const validateTask = validate35;
const schema46 = {"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/LegacyTask"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebTask"}]};
const schema47 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"tenant_id":{"format":"uuid","title":"Tenant Id","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"name":{"maxLength":120,"minLength":1,"title":"Name","type":"string"},"target_url":{"maxLength":2048,"minLength":1,"title":"Target Url","type":"string"},"scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel"},"version":{"maximum":9007199254740991,"minimum":1,"title":"Version","type":"integer"},"state":{"enum":["queued","cancelled"],"title":"State","type":"string"},"cleanup_state":{"const":"not_required","title":"Cleanup State","type":"string"},"execution":{"$ref":"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse"},"allowed_actions":{"items":{"const":"cancel","type":"string"},"maxItems":1,"title":"Allowed Actions","type":"array"},"assessment_outcome":{"const":"not_assessed","title":"Assessment Outcome","type":"string"},"stop_reason":{"anyOf":[{"const":"user_cancelled","type":"string"},{"type":"null"}],"title":"Stop Reason"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","tenant_id","project_id","name","target_url","scope","version","state","cleanup_state","execution","allowed_actions","assessment_outcome","stop_reason","created_at","updated_at"],"title":"TaskResponse","type":"object"};
const schema48 = {"additionalProperties":false,"properties":{"policy_id":{"format":"uuid","title":"Policy Id","type":"string"},"version":{"maximum":9007199254740991,"minimum":1,"title":"Version","type":"integer"}},"required":["policy_id","version"],"title":"ScopeBindingModel","type":"object"};
const schema49 = {"additionalProperties":false,"properties":{"active_calls":{"maximum":9007199254740991,"minimum":0,"title":"Active Calls","type":"integer"},"unknown_calls":{"maximum":9007199254740991,"minimum":0,"title":"Unknown Calls","type":"integer"},"egress_state":{"const":"not_granted","title":"Egress State","type":"string"}},"required":["active_calls","unknown_calls","egress_state"],"title":"ExecutionSummaryResponse","type":"object"};
const func22 = Object.prototype.hasOwnProperty;

function validate36(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate36.evaluated;
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
if(data.project_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.name === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.target_url === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.scope === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scope"},message:"must have required property '"+"scope"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.version === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.state === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.cleanup_state === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cleanup_state"},message:"must have required property '"+"cleanup_state"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.execution === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "execution"},message:"must have required property '"+"execution"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.allowed_actions === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_actions"},message:"must have required property '"+"allowed_actions"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.assessment_outcome === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "assessment_outcome"},message:"must have required property '"+"assessment_outcome"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data.stop_reason === undefined){
const err12 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "stop_reason"},message:"must have required property '"+"stop_reason"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data.created_at === undefined){
const err13 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data.updated_at === undefined){
const err14 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema47.properties, key0))){
const err15 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err16 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err17 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err18 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err19 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
let data2 = data.project_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
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
if(data.name !== undefined){
let data3 = data.name;
if(typeof data3 === "string"){
if(func1(data3) > 120){
const err22 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(func1(data3) < 1){
const err23 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
else {
const err24 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data.target_url !== undefined){
let data4 = data.target_url;
if(typeof data4 === "string"){
if(func1(data4) > 2048){
const err25 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(func1(data4) < 1){
const err26 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err27 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data.scope !== undefined){
let data5 = data.scope;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.policy_id === undefined){
const err28 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/required",keyword:"required",params:{missingProperty: "policy_id"},message:"must have required property '"+"policy_id"+"'"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data5.version === undefined){
const err29 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
for(const key1 in data5){
if(!((key1 === "policy_id") || (key1 === "version"))){
const err30 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data5.policy_id !== undefined){
let data6 = data5.policy_id;
if(typeof data6 === "string"){
if(!(formats0.test(data6))){
const err31 = {instancePath:instancePath+"/scope/policy_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/properties/policy_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
else {
const err32 = {instancePath:instancePath+"/scope/policy_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/properties/policy_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data5.version !== undefined){
let data7 = data5.version;
if(!(((typeof data7 == "number") && (!(data7 % 1) && !isNaN(data7))) && (isFinite(data7)))){
const err33 = {instancePath:instancePath+"/scope/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 > 9007199254740991 || isNaN(data7)){
const err34 = {instancePath:instancePath+"/scope/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/properties/version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(data7 < 1 || isNaN(data7)){
const err35 = {instancePath:instancePath+"/scope/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
}
else {
const err36 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScopeBindingModel/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
if(data.version !== undefined){
let data8 = data.version;
if(!(((typeof data8 == "number") && (!(data8 % 1) && !isNaN(data8))) && (isFinite(data8)))){
const err37 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if((typeof data8 == "number") && (isFinite(data8))){
if(data8 > 9007199254740991 || isNaN(data8)){
const err38 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
if(data8 < 1 || isNaN(data8)){
const err39 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data.state !== undefined){
let data9 = data.state;
if(typeof data9 !== "string"){
const err40 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if(!((data9 === "queued") || (data9 === "cancelled"))){
const err41 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema47.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
if(data.cleanup_state !== undefined){
let data10 = data.cleanup_state;
if(typeof data10 !== "string"){
const err42 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
if("not_required" !== data10){
const err43 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/const",keyword:"const",params:{allowedValue: "not_required"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
if(data.execution !== undefined){
let data11 = data.execution;
if(data11 && typeof data11 == "object" && !Array.isArray(data11)){
if(data11.active_calls === undefined){
const err44 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "active_calls"},message:"must have required property '"+"active_calls"+"'"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
if(data11.unknown_calls === undefined){
const err45 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "unknown_calls"},message:"must have required property '"+"unknown_calls"+"'"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if(data11.egress_state === undefined){
const err46 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "egress_state"},message:"must have required property '"+"egress_state"+"'"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
for(const key2 in data11){
if(!(((key2 === "active_calls") || (key2 === "unknown_calls")) || (key2 === "egress_state"))){
const err47 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
if(data11.active_calls !== undefined){
let data12 = data11.active_calls;
if(!(((typeof data12 == "number") && (!(data12 % 1) && !isNaN(data12))) && (isFinite(data12)))){
const err48 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/active_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
if((typeof data12 == "number") && (isFinite(data12))){
if(data12 > 9007199254740991 || isNaN(data12)){
const err49 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/active_calls/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
if(data12 < 0 || isNaN(data12)){
const err50 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/active_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
}
if(data11.unknown_calls !== undefined){
let data13 = data11.unknown_calls;
if(!(((typeof data13 == "number") && (!(data13 % 1) && !isNaN(data13))) && (isFinite(data13)))){
const err51 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/unknown_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
if((typeof data13 == "number") && (isFinite(data13))){
if(data13 > 9007199254740991 || isNaN(data13)){
const err52 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/unknown_calls/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
if(data13 < 0 || isNaN(data13)){
const err53 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/unknown_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
}
if(data11.egress_state !== undefined){
let data14 = data11.egress_state;
if(typeof data14 !== "string"){
const err54 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/egress_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
if("not_granted" !== data14){
const err55 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/properties/egress_state/const",keyword:"const",params:{allowedValue: "not_granted"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
}
}
else {
const err56 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExecutionSummaryResponse/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
}
if(data.allowed_actions !== undefined){
let data15 = data.allowed_actions;
if(Array.isArray(data15)){
if(data15.length > 1){
const err57 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/maxItems",keyword:"maxItems",params:{limit: 1},message:"must NOT have more than 1 items"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
const len0 = data15.length;
for(let i0=0; i0<len0; i0++){
let data16 = data15[i0];
if(typeof data16 !== "string"){
const err58 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"#/properties/allowed_actions/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
if("cancel" !== data16){
const err59 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"#/properties/allowed_actions/items/const",keyword:"const",params:{allowedValue: "cancel"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
}
}
else {
const err60 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
}
if(data.assessment_outcome !== undefined){
let data17 = data.assessment_outcome;
if(typeof data17 !== "string"){
const err61 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
if("not_assessed" !== data17){
const err62 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/const",keyword:"const",params:{allowedValue: "not_assessed"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
if(data.stop_reason !== undefined){
let data18 = data.stop_reason;
const _errs43 = errors;
let valid7 = false;
const _errs44 = errors;
if(typeof data18 !== "string"){
const err63 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
if("user_cancelled" !== data18){
const err64 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf/0/const",keyword:"const",params:{allowedValue: "user_cancelled"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
var _valid0 = _errs44 === errors;
valid7 = valid7 || _valid0;
const _errs46 = errors;
if(data18 !== null){
const err65 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
var _valid0 = _errs46 === errors;
valid7 = valid7 || _valid0;
if(!valid7){
const err66 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
else {
errors = _errs43;
if(vErrors !== null){
if(_errs43){
vErrors.length = _errs43;
}
else {
vErrors = null;
}
}
}
}
if(data.created_at !== undefined){
let data19 = data.created_at;
if(typeof data19 === "string"){
if(!(formats2.validate(data19))){
const err67 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
}
else {
const err68 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data20 = data.updated_at;
if(typeof data20 === "string"){
if(!(formats2.validate(data20))){
const err69 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
}
else {
const err70 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
}
else {
const err71 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
validate36.errors = vErrors;
return errors === 0;
}
validate36.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema50 = {"additionalProperties":false,"properties":{"task_kind":{"const":"web_assessment","default":"web_assessment","title":"Task Kind","type":"string"},"id":{"format":"uuid","title":"Id","type":"string"},"tenant_id":{"format":"uuid","title":"Tenant Id","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"name":{"maxLength":120,"minLength":1,"title":"Name","type":"string"},"target_url":{"maxLength":2048,"minLength":1,"title":"Target Url","type":"string"},"scope":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse"},"version":{"maximum":9007199254740991,"minimum":1,"title":"Version","type":"integer"},"state":{"enum":["ready","provisioning","running","completing","completed","cancelling","cancelled","reconciling"],"title":"State","type":"string"},"cleanup_state":{"enum":["not_required","pending","running","completed","failed","unknown"],"title":"Cleanup State","type":"string"},"execution":{"$ref":"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse"},"allowed_actions":{"items":{"enum":["start","cancel"],"type":"string"},"maxItems":2,"title":"Allowed Actions","type":"array"},"assessment_outcome":{"enum":["not_assessed","complete","partial","inconclusive"],"title":"Assessment Outcome","type":"string"},"stop_reason":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Stop Reason"},"creation_config":{"$ref":"urn:wuji:contracts:0.5#/$defs/CreationConfigSnapshot"},"start_blockers":{"items":{"type":"string"},"maxItems":20,"title":"Start Blockers","type":"array"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","tenant_id","project_id","name","target_url","scope","version","state","cleanup_state","execution","allowed_actions","assessment_outcome","stop_reason","creation_config","created_at","updated_at"],"title":"WebTaskResponse","type":"object"};
const schema51 = {"additionalProperties":false,"properties":{"authorization_id":{"format":"uuid","title":"Authorization Id","type":"string"},"version":{"minimum":1,"title":"Version","type":"integer"},"hash":{"pattern":"^[a-f0-9]{64}$","title":"Hash","type":"string"}},"required":["authorization_id","version","hash"],"title":"TaskAuthorizationBindingResponse","type":"object"};
const schema52 = {"additionalProperties":false,"properties":{"active_calls":{"minimum":0,"title":"Active Calls","type":"integer"},"unknown_calls":{"minimum":0,"title":"Unknown Calls","type":"integer"},"egress_state":{"enum":["not_granted","fixture_only","revoking","revoked","unknown"],"title":"Egress State","type":"string"}},"required":["active_calls","unknown_calls","egress_state"],"title":"WebExecutionSummaryResponse","type":"object"};
const schema53 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"id":{"format":"uuid","title":"Id","type":"string"},"scenario":{"const":"web_single","title":"Scenario","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}]},"objective":{"maxLength":8000,"minLength":1,"title":"Objective","type":"string"},"completion_criteria":{"items":{"type":"string"},"maxItems":20,"minItems":1,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"maxLength":8000,"title":"Supplemental Hints","type":"string"},"actual_input":{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraftV2"}],"title":"Actual Input"},"authorization":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskAuthorization"},"authorization_id":{"format":"uuid","title":"Authorization Id","type":"string"},"authorization_digest":{"pattern":"^[a-f0-9]{64}$","title":"Authorization Digest","type":"string"},"model":{"$ref":"urn:wuji:contracts:0.5#/$defs/SelectedModelSnapshot"},"budget_usd":{"title":"Budget Usd","type":"string"},"created_by":{"format":"uuid","title":"Created By","type":"string"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"digest":{"pattern":"^[a-f0-9]{64}$","title":"Digest","type":"string"}},"required":["schema_version","id","scenario","goal_template","objective","completion_criteria","supplemental_hints","actual_input","authorization","authorization_id","authorization_digest","model","budget_usd","created_by","created_at","digest"],"title":"CreationConfigSnapshot","type":"object"};
const schema54 = {"additionalProperties":false,"properties":{"id":{"maxLength":120,"minLength":1,"title":"Id","type":"string"},"version":{"minimum":1,"title":"Version","type":"integer"},"digest":{"pattern":"^[a-f0-9]{64}$","title":"Digest","type":"string"}},"required":["id","version","digest"],"title":"GoalTemplateReference","type":"object"};
const schema55 = {"additionalProperties":false,"properties":{"schema_version":{"const":"2.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}],"default":null},"completion_criteria":{"items":{"maxLength":1000,"type":"string"},"maxItems":20,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"default":"","maxLength":8000,"title":"Supplemental Hints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"title":"Budget Usd"},"scenario":{"const":"ctf","title":"Scenario","type":"string"},"challenge":{"default":"","maxLength":8000,"title":"Challenge","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"}},"required":["schema_version","scenario"],"title":"CtfDraftV2","type":"object"};
const pattern10 = new RegExp("^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$", "u");

function validate40(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate40.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scenario === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema55.properties, key0))){
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
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err3 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if("2.0" !== data0){
const err4 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "2.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.name !== undefined){
let data1 = data.name;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err5 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err6 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.objective !== undefined){
let data2 = data.objective;
if(typeof data2 === "string"){
if(func1(data2) > 8000){
const err7 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err8 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err9 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data3.version === undefined){
const err10 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data3.digest === undefined){
const err11 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err12 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err13 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(func1(data4) < 1){
const err14 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err15 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err16 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err17 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err18 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err19 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err21 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err22 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.completion_criteria !== undefined){
let data7 = data.completion_criteria;
if(Array.isArray(data7)){
if(data7.length > 20){
const err23 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(typeof data8 === "string"){
if(func1(data8) > 1000){
const err24 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/maxLength",keyword:"maxLength",params:{limit: 1000},message:"must NOT have more than 1000 characters"};
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
const err25 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data9 = data.supplemental_hints;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err27 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.reference_ids !== undefined){
let data10 = data.reference_ids;
if(Array.isArray(data10)){
if(data10.length > 20){
const err29 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len1 = data10.length;
for(let i1=0; i1<len1; i1++){
let data11 = data10[i1];
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err30 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.model_profile_version_id !== undefined){
let data12 = data.model_profile_version_id;
const _errs33 = errors;
let valid8 = false;
const _errs34 = errors;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid8 = valid8 || _valid1;
const _errs36 = errors;
if(data12 !== null){
const err35 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid8 = valid8 || _valid1;
if(!valid8){
const err36 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data.runtime_profile_version_id !== undefined){
let data13 = data.runtime_profile_version_id;
const _errs39 = errors;
let valid9 = false;
const _errs40 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err37 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
else {
const err38 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid9 = valid9 || _valid2;
const _errs42 = errors;
if(data13 !== null){
const err39 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid9 = valid9 || _valid2;
if(!valid9){
const err40 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data.budget_usd !== undefined){
let data14 = data.budget_usd;
const _errs45 = errors;
let valid10 = false;
const _errs46 = errors;
if(typeof data14 === "string"){
if(!pattern10.test(data14)){
const err41 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid10 = valid10 || _valid3;
const _errs48 = errors;
if(data14 !== null){
const err43 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid10 = valid10 || _valid3;
if(!valid10){
const err44 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
}
if(data.scenario !== undefined){
let data15 = data.scenario;
if(typeof data15 !== "string"){
const err45 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if("ctf" !== data15){
const err46 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "ctf"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.challenge !== undefined){
let data16 = data.challenge;
if(typeof data16 === "string"){
if(func1(data16) > 8000){
const err47 = {instancePath:instancePath+"/challenge",schemaPath:"#/properties/challenge/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/challenge",schemaPath:"#/properties/challenge/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data.entry_url !== undefined){
let data17 = data.entry_url;
const _errs55 = errors;
let valid11 = false;
const _errs56 = errors;
if(typeof data17 === "string"){
if(func1(data17) > 2048){
const err49 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
else {
const err50 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
var _valid4 = _errs56 === errors;
valid11 = valid11 || _valid4;
const _errs58 = errors;
if(data17 !== null){
const err51 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
var _valid4 = _errs58 === errors;
valid11 = valid11 || _valid4;
if(!valid11){
const err52 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
else {
errors = _errs55;
if(vErrors !== null){
if(_errs55){
vErrors.length = _errs55;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err53 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
validate40.errors = vErrors;
return errors === 0;
}
validate40.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema57 = {"additionalProperties":false,"properties":{"schema_version":{"const":"2.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}],"default":null},"completion_criteria":{"items":{"maxLength":1000,"type":"string"},"maxItems":20,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"default":"","maxLength":8000,"title":"Supplemental Hints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"title":"Budget Usd"},"scenario":{"const":"web_single","title":"Scenario","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"},"authorization":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskAuthorization"},{"type":"null"}],"default":null}},"required":["schema_version","scenario"],"title":"WebDraftV2","type":"object"};
const schema59 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"includes":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/IncludeRule"},"maxItems":100,"title":"Includes","type":"array"},"excludes":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ExcludeRule"},"maxItems":100,"title":"Excludes","type":"array"},"valid_until":{"anyOf":[{"format":"date-time","type":"string"},{"type":"null"}],"default":null,"title":"Valid Until"}},"title":"TaskAuthorization","type":"object"};
const schema60 = {"additionalProperties":false,"properties":{"host":{"maxLength":253,"minLength":1,"title":"Host","type":"string"},"include_subdomains":{"default":false,"title":"Include Subdomains","type":"boolean"},"endpoint":{"$ref":"urn:wuji:contracts:0.5#/$defs/Endpoint"}},"required":["host","endpoint"],"title":"IncludeRule","type":"object"};
const schema61 = {"additionalProperties":false,"properties":{"scheme":{"enum":["http","https"],"title":"Scheme","type":"string"},"port":{"maximum":65535,"minimum":1,"title":"Port","type":"integer"}},"required":["scheme","port"],"title":"Endpoint","type":"object"};

function validate44(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate44.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.host === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "host"},message:"must have required property '"+"host"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.endpoint === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "endpoint"},message:"must have required property '"+"endpoint"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(((key0 === "host") || (key0 === "include_subdomains")) || (key0 === "endpoint"))){
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
if(data.host !== undefined){
let data0 = data.host;
if(typeof data0 === "string"){
if(func1(data0) > 253){
const err3 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(func1(data0) < 1){
const err4 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
else {
const err5 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.include_subdomains !== undefined){
if(typeof data.include_subdomains !== "boolean"){
const err6 = {instancePath:instancePath+"/include_subdomains",schemaPath:"#/properties/include_subdomains/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.endpoint !== undefined){
let data2 = data.endpoint;
if(data2 && typeof data2 == "object" && !Array.isArray(data2)){
if(data2.scheme === undefined){
const err7 = {instancePath:instancePath+"/endpoint",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/required",keyword:"required",params:{missingProperty: "scheme"},message:"must have required property '"+"scheme"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data2.port === undefined){
const err8 = {instancePath:instancePath+"/endpoint",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/required",keyword:"required",params:{missingProperty: "port"},message:"must have required property '"+"port"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
for(const key1 in data2){
if(!((key1 === "scheme") || (key1 === "port"))){
const err9 = {instancePath:instancePath+"/endpoint",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data2.scheme !== undefined){
let data3 = data2.scheme;
if(typeof data3 !== "string"){
const err10 = {instancePath:instancePath+"/endpoint/scheme",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/scheme/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(!((data3 === "http") || (data3 === "https"))){
const err11 = {instancePath:instancePath+"/endpoint/scheme",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/scheme/enum",keyword:"enum",params:{allowedValues: schema61.properties.scheme.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data2.port !== undefined){
let data4 = data2.port;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err12 = {instancePath:instancePath+"/endpoint/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 65535 || isNaN(data4)){
const err13 = {instancePath:instancePath+"/endpoint/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/maximum",keyword:"maximum",params:{comparison: "<=", limit: 65535},message:"must be <= 65535"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err14 = {instancePath:instancePath+"/endpoint/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
}
else {
const err15 = {instancePath:instancePath+"/endpoint",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
validate44.errors = vErrors;
return errors === 0;
}
validate44.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema62 = {"additionalProperties":false,"properties":{"host":{"maxLength":253,"minLength":1,"title":"Host","type":"string"},"include_subdomains":{"default":false,"title":"Include Subdomains","type":"boolean"},"endpoints":{"anyOf":[{"const":"all_included","type":"string"},{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Endpoint"},"type":"array"}],"default":"all_included","title":"Endpoints"}},"required":["host"],"title":"ExcludeRule","type":"object"};

function validate46(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate46.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.host === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "host"},message:"must have required property '"+"host"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
for(const key0 in data){
if(!(((key0 === "host") || (key0 === "include_subdomains")) || (key0 === "endpoints"))){
const err1 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
}
if(data.host !== undefined){
let data0 = data.host;
if(typeof data0 === "string"){
if(func1(data0) > 253){
const err2 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(func1(data0) < 1){
const err3 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err4 = {instancePath:instancePath+"/host",schemaPath:"#/properties/host/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.include_subdomains !== undefined){
if(typeof data.include_subdomains !== "boolean"){
const err5 = {instancePath:instancePath+"/include_subdomains",schemaPath:"#/properties/include_subdomains/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.endpoints !== undefined){
let data2 = data.endpoints;
const _errs7 = errors;
let valid1 = false;
const _errs8 = errors;
if(typeof data2 !== "string"){
const err6 = {instancePath:instancePath+"/endpoints",schemaPath:"#/properties/endpoints/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if("all_included" !== data2){
const err7 = {instancePath:instancePath+"/endpoints",schemaPath:"#/properties/endpoints/anyOf/0/const",keyword:"const",params:{allowedValue: "all_included"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid0 = _errs8 === errors;
valid1 = valid1 || _valid0;
const _errs10 = errors;
if(Array.isArray(data2)){
const len0 = data2.length;
for(let i0=0; i0<len0; i0++){
let data3 = data2[i0];
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.scheme === undefined){
const err8 = {instancePath:instancePath+"/endpoints/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/required",keyword:"required",params:{missingProperty: "scheme"},message:"must have required property '"+"scheme"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data3.port === undefined){
const err9 = {instancePath:instancePath+"/endpoints/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/required",keyword:"required",params:{missingProperty: "port"},message:"must have required property '"+"port"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
for(const key1 in data3){
if(!((key1 === "scheme") || (key1 === "port"))){
const err10 = {instancePath:instancePath+"/endpoints/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data3.scheme !== undefined){
let data4 = data3.scheme;
if(typeof data4 !== "string"){
const err11 = {instancePath:instancePath+"/endpoints/" + i0+"/scheme",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/scheme/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(!((data4 === "http") || (data4 === "https"))){
const err12 = {instancePath:instancePath+"/endpoints/" + i0+"/scheme",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/scheme/enum",keyword:"enum",params:{allowedValues: schema61.properties.scheme.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.port !== undefined){
let data5 = data3.port;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err13 = {instancePath:instancePath+"/endpoints/" + i0+"/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 > 65535 || isNaN(data5)){
const err14 = {instancePath:instancePath+"/endpoints/" + i0+"/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/maximum",keyword:"maximum",params:{comparison: "<=", limit: 65535},message:"must be <= 65535"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data5 < 1 || isNaN(data5)){
const err15 = {instancePath:instancePath+"/endpoints/" + i0+"/port",schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/properties/port/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
}
else {
const err16 = {instancePath:instancePath+"/endpoints/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Endpoint/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
}
else {
const err17 = {instancePath:instancePath+"/endpoints",schemaPath:"#/properties/endpoints/anyOf/1/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err18 = {instancePath:instancePath+"/endpoints",schemaPath:"#/properties/endpoints/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
else {
errors = _errs7;
if(vErrors !== null){
if(_errs7){
vErrors.length = _errs7;
}
else {
vErrors = null;
}
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
validate46.errors = vErrors;
return errors === 0;
}
validate46.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate43(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate43.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
for(const key0 in data){
if(!((((key0 === "schema_version") || (key0 === "includes")) || (key0 === "excludes")) || (key0 === "valid_until"))){
const err0 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
}
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err1 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if("1.0" !== data0){
const err2 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
}
if(data.includes !== undefined){
let data1 = data.includes;
if(Array.isArray(data1)){
if(data1.length > 100){
const err3 = {instancePath:instancePath+"/includes",schemaPath:"#/properties/includes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
const len0 = data1.length;
for(let i0=0; i0<len0; i0++){
if(!(validate44(data1[i0], {instancePath:instancePath+"/includes/" + i0,parentData:data1,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate44.errors : vErrors.concat(validate44.errors);
errors = vErrors.length;
}
}
}
else {
const err4 = {instancePath:instancePath+"/includes",schemaPath:"#/properties/includes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.excludes !== undefined){
let data3 = data.excludes;
if(Array.isArray(data3)){
if(data3.length > 100){
const err5 = {instancePath:instancePath+"/excludes",schemaPath:"#/properties/excludes/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
const len1 = data3.length;
for(let i1=0; i1<len1; i1++){
if(!(validate46(data3[i1], {instancePath:instancePath+"/excludes/" + i1,parentData:data3,parentDataProperty:i1,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate46.errors : vErrors.concat(validate46.errors);
errors = vErrors.length;
}
}
}
else {
const err6 = {instancePath:instancePath+"/excludes",schemaPath:"#/properties/excludes/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.valid_until !== undefined){
let data5 = data.valid_until;
const _errs11 = errors;
let valid5 = false;
const _errs12 = errors;
if(typeof data5 === "string"){
if(!(formats2.validate(data5))){
const err7 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/anyOf/0/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
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
const err8 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
var _valid0 = _errs12 === errors;
valid5 = valid5 || _valid0;
const _errs14 = errors;
if(data5 !== null){
const err9 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
var _valid0 = _errs14 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err10 = {instancePath:instancePath+"/valid_until",schemaPath:"#/properties/valid_until/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
else {
errors = _errs11;
if(vErrors !== null){
if(_errs11){
vErrors.length = _errs11;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err11 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
validate43.errors = vErrors;
return errors === 0;
}
validate43.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate42(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate42.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scenario === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema57.properties, key0))){
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
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err3 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if("2.0" !== data0){
const err4 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "2.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.name !== undefined){
let data1 = data.name;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err5 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err6 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.objective !== undefined){
let data2 = data.objective;
if(typeof data2 === "string"){
if(func1(data2) > 8000){
const err7 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err8 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err9 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data3.version === undefined){
const err10 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data3.digest === undefined){
const err11 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err12 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err13 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(func1(data4) < 1){
const err14 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err15 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err16 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err17 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err18 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err19 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err21 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err22 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.completion_criteria !== undefined){
let data7 = data.completion_criteria;
if(Array.isArray(data7)){
if(data7.length > 20){
const err23 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(typeof data8 === "string"){
if(func1(data8) > 1000){
const err24 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/maxLength",keyword:"maxLength",params:{limit: 1000},message:"must NOT have more than 1000 characters"};
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
const err25 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data9 = data.supplemental_hints;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err27 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.reference_ids !== undefined){
let data10 = data.reference_ids;
if(Array.isArray(data10)){
if(data10.length > 20){
const err29 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len1 = data10.length;
for(let i1=0; i1<len1; i1++){
let data11 = data10[i1];
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err30 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.model_profile_version_id !== undefined){
let data12 = data.model_profile_version_id;
const _errs33 = errors;
let valid8 = false;
const _errs34 = errors;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid8 = valid8 || _valid1;
const _errs36 = errors;
if(data12 !== null){
const err35 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid8 = valid8 || _valid1;
if(!valid8){
const err36 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data.runtime_profile_version_id !== undefined){
let data13 = data.runtime_profile_version_id;
const _errs39 = errors;
let valid9 = false;
const _errs40 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err37 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
else {
const err38 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid9 = valid9 || _valid2;
const _errs42 = errors;
if(data13 !== null){
const err39 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid9 = valid9 || _valid2;
if(!valid9){
const err40 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data.budget_usd !== undefined){
let data14 = data.budget_usd;
const _errs45 = errors;
let valid10 = false;
const _errs46 = errors;
if(typeof data14 === "string"){
if(!pattern10.test(data14)){
const err41 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid10 = valid10 || _valid3;
const _errs48 = errors;
if(data14 !== null){
const err43 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid10 = valid10 || _valid3;
if(!valid10){
const err44 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
}
if(data.scenario !== undefined){
let data15 = data.scenario;
if(typeof data15 !== "string"){
const err45 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if("web_single" !== data15){
const err46 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "web_single"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.entry_url !== undefined){
let data16 = data.entry_url;
const _errs53 = errors;
let valid11 = false;
const _errs54 = errors;
if(typeof data16 === "string"){
if(func1(data16) > 2048){
const err47 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
var _valid4 = _errs54 === errors;
valid11 = valid11 || _valid4;
const _errs56 = errors;
if(data16 !== null){
const err49 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
var _valid4 = _errs56 === errors;
valid11 = valid11 || _valid4;
if(!valid11){
const err50 = {instancePath:instancePath+"/entry_url",schemaPath:"#/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
else {
errors = _errs53;
if(vErrors !== null){
if(_errs53){
vErrors.length = _errs53;
}
else {
vErrors = null;
}
}
}
}
if(data.authorization !== undefined){
let data17 = data.authorization;
const _errs59 = errors;
let valid12 = false;
const _errs60 = errors;
if(!(validate43(data17, {instancePath:instancePath+"/authorization",parentData:data,parentDataProperty:"authorization",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate43.errors : vErrors.concat(validate43.errors);
errors = vErrors.length;
}
var _valid5 = _errs60 === errors;
valid12 = valid12 || _valid5;
const _errs61 = errors;
if(data17 !== null){
const err51 = {instancePath:instancePath+"/authorization",schemaPath:"#/properties/authorization/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
var _valid5 = _errs61 === errors;
valid12 = valid12 || _valid5;
if(!valid12){
const err52 = {instancePath:instancePath+"/authorization",schemaPath:"#/properties/authorization/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
else {
errors = _errs59;
if(vErrors !== null){
if(_errs59){
vErrors.length = _errs59;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err53 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
validate42.errors = vErrors;
return errors === 0;
}
validate42.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema64 = {"additionalProperties":false,"properties":{"schema_version":{"const":"2.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}],"default":null},"completion_criteria":{"items":{"maxLength":1000,"type":"string"},"maxItems":20,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"default":"","maxLength":8000,"title":"Supplemental Hints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"title":"Budget Usd"},"scenario":{"const":"comprehensive","title":"Scenario","type":"string"},"assets":{"items":{"maxLength":2048,"type":"string"},"maxItems":100,"title":"Assets","type":"array"},"access_notes":{"default":"","maxLength":4000,"title":"Access Notes","type":"string"}},"required":["schema_version","scenario"],"title":"ComprehensiveDraftV2","type":"object"};

function validate50(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate50.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scenario === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema64.properties, key0))){
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
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err3 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if("2.0" !== data0){
const err4 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "2.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.name !== undefined){
let data1 = data.name;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err5 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err6 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.objective !== undefined){
let data2 = data.objective;
if(typeof data2 === "string"){
if(func1(data2) > 8000){
const err7 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err8 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err9 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data3.version === undefined){
const err10 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data3.digest === undefined){
const err11 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err12 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err13 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(func1(data4) < 1){
const err14 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err15 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err16 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err17 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err18 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err19 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err21 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err22 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.completion_criteria !== undefined){
let data7 = data.completion_criteria;
if(Array.isArray(data7)){
if(data7.length > 20){
const err23 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(typeof data8 === "string"){
if(func1(data8) > 1000){
const err24 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/maxLength",keyword:"maxLength",params:{limit: 1000},message:"must NOT have more than 1000 characters"};
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
const err25 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data9 = data.supplemental_hints;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err27 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.reference_ids !== undefined){
let data10 = data.reference_ids;
if(Array.isArray(data10)){
if(data10.length > 20){
const err29 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len1 = data10.length;
for(let i1=0; i1<len1; i1++){
let data11 = data10[i1];
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err30 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.model_profile_version_id !== undefined){
let data12 = data.model_profile_version_id;
const _errs33 = errors;
let valid8 = false;
const _errs34 = errors;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid8 = valid8 || _valid1;
const _errs36 = errors;
if(data12 !== null){
const err35 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid8 = valid8 || _valid1;
if(!valid8){
const err36 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data.runtime_profile_version_id !== undefined){
let data13 = data.runtime_profile_version_id;
const _errs39 = errors;
let valid9 = false;
const _errs40 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err37 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
else {
const err38 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid9 = valid9 || _valid2;
const _errs42 = errors;
if(data13 !== null){
const err39 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid9 = valid9 || _valid2;
if(!valid9){
const err40 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data.budget_usd !== undefined){
let data14 = data.budget_usd;
const _errs45 = errors;
let valid10 = false;
const _errs46 = errors;
if(typeof data14 === "string"){
if(!pattern10.test(data14)){
const err41 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid10 = valid10 || _valid3;
const _errs48 = errors;
if(data14 !== null){
const err43 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid10 = valid10 || _valid3;
if(!valid10){
const err44 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
}
if(data.scenario !== undefined){
let data15 = data.scenario;
if(typeof data15 !== "string"){
const err45 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if("comprehensive" !== data15){
const err46 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "comprehensive"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.assets !== undefined){
let data16 = data.assets;
if(Array.isArray(data16)){
if(data16.length > 100){
const err47 = {instancePath:instancePath+"/assets",schemaPath:"#/properties/assets/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
const len2 = data16.length;
for(let i2=0; i2<len2; i2++){
let data17 = data16[i2];
if(typeof data17 === "string"){
if(func1(data17) > 2048){
const err48 = {instancePath:instancePath+"/assets/" + i2,schemaPath:"#/properties/assets/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
else {
const err49 = {instancePath:instancePath+"/assets/" + i2,schemaPath:"#/properties/assets/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
}
else {
const err50 = {instancePath:instancePath+"/assets",schemaPath:"#/properties/assets/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
if(data.access_notes !== undefined){
let data18 = data.access_notes;
if(typeof data18 === "string"){
if(func1(data18) > 4000){
const err51 = {instancePath:instancePath+"/access_notes",schemaPath:"#/properties/access_notes/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
else {
const err52 = {instancePath:instancePath+"/access_notes",schemaPath:"#/properties/access_notes/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
}
else {
const err53 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
validate50.errors = vErrors;
return errors === 0;
}
validate50.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema66 = {"additionalProperties":false,"properties":{"schema_version":{"const":"2.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}],"default":null},"completion_criteria":{"items":{"maxLength":1000,"type":"string"},"maxItems":20,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"default":"","maxLength":8000,"title":"Supplemental Hints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"title":"Budget Usd"},"scenario":{"const":"exercise","title":"Scenario","type":"string"},"organization_name":{"default":"","maxLength":255,"title":"Organization Name","type":"string"},"known_domains":{"items":{"maxLength":253,"type":"string"},"maxItems":100,"title":"Known Domains","type":"array"}},"required":["schema_version","scenario"],"title":"ExerciseDraftV2","type":"object"};

function validate52(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate52.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scenario === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema66.properties, key0))){
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
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err3 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if("2.0" !== data0){
const err4 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "2.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.name !== undefined){
let data1 = data.name;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err5 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err6 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.objective !== undefined){
let data2 = data.objective;
if(typeof data2 === "string"){
if(func1(data2) > 8000){
const err7 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err8 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err9 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data3.version === undefined){
const err10 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data3.digest === undefined){
const err11 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err12 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err13 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(func1(data4) < 1){
const err14 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err15 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err16 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err17 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err18 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err19 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err21 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err22 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.completion_criteria !== undefined){
let data7 = data.completion_criteria;
if(Array.isArray(data7)){
if(data7.length > 20){
const err23 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(typeof data8 === "string"){
if(func1(data8) > 1000){
const err24 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/maxLength",keyword:"maxLength",params:{limit: 1000},message:"must NOT have more than 1000 characters"};
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
const err25 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data9 = data.supplemental_hints;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err27 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.reference_ids !== undefined){
let data10 = data.reference_ids;
if(Array.isArray(data10)){
if(data10.length > 20){
const err29 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len1 = data10.length;
for(let i1=0; i1<len1; i1++){
let data11 = data10[i1];
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err30 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.model_profile_version_id !== undefined){
let data12 = data.model_profile_version_id;
const _errs33 = errors;
let valid8 = false;
const _errs34 = errors;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid8 = valid8 || _valid1;
const _errs36 = errors;
if(data12 !== null){
const err35 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid8 = valid8 || _valid1;
if(!valid8){
const err36 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data.runtime_profile_version_id !== undefined){
let data13 = data.runtime_profile_version_id;
const _errs39 = errors;
let valid9 = false;
const _errs40 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err37 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
else {
const err38 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid9 = valid9 || _valid2;
const _errs42 = errors;
if(data13 !== null){
const err39 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid9 = valid9 || _valid2;
if(!valid9){
const err40 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data.budget_usd !== undefined){
let data14 = data.budget_usd;
const _errs45 = errors;
let valid10 = false;
const _errs46 = errors;
if(typeof data14 === "string"){
if(!pattern10.test(data14)){
const err41 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid10 = valid10 || _valid3;
const _errs48 = errors;
if(data14 !== null){
const err43 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid10 = valid10 || _valid3;
if(!valid10){
const err44 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
}
if(data.scenario !== undefined){
let data15 = data.scenario;
if(typeof data15 !== "string"){
const err45 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if("exercise" !== data15){
const err46 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "exercise"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.organization_name !== undefined){
let data16 = data.organization_name;
if(typeof data16 === "string"){
if(func1(data16) > 255){
const err47 = {instancePath:instancePath+"/organization_name",schemaPath:"#/properties/organization_name/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/organization_name",schemaPath:"#/properties/organization_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data.known_domains !== undefined){
let data17 = data.known_domains;
if(Array.isArray(data17)){
if(data17.length > 100){
const err49 = {instancePath:instancePath+"/known_domains",schemaPath:"#/properties/known_domains/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
const len2 = data17.length;
for(let i2=0; i2<len2; i2++){
let data18 = data17[i2];
if(typeof data18 === "string"){
if(func1(data18) > 253){
const err50 = {instancePath:instancePath+"/known_domains/" + i2,schemaPath:"#/properties/known_domains/items/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
else {
const err51 = {instancePath:instancePath+"/known_domains/" + i2,schemaPath:"#/properties/known_domains/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err52 = {instancePath:instancePath+"/known_domains",schemaPath:"#/properties/known_domains/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
}
else {
const err53 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
validate52.errors = vErrors;
return errors === 0;
}
validate52.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema68 = {"additionalProperties":false,"properties":{"schema_version":{"const":"2.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"goal_template":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference"},{"type":"null"}],"default":null},"completion_criteria":{"items":{"maxLength":1000,"type":"string"},"maxItems":20,"title":"Completion Criteria","type":"array"},"supplemental_hints":{"default":"","maxLength":8000,"title":"Supplemental Hints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"title":"Budget Usd"},"scenario":{"const":"code_audit","title":"Scenario","type":"string"},"repository_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Repository Url"},"source_reference_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Source Reference Id"},"revision":{"anyOf":[{"maxLength":255,"type":"string"},{"type":"null"}],"default":null,"title":"Revision"}},"required":["schema_version","scenario"],"title":"CodeAuditDraftV2","type":"object"};

function validate54(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate54.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.scenario === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema68.properties, key0))){
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
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err3 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if("2.0" !== data0){
const err4 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "2.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.name !== undefined){
let data1 = data.name;
if(typeof data1 === "string"){
if(func1(data1) > 120){
const err5 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err6 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
}
if(data.objective !== undefined){
let data2 = data.objective;
if(typeof data2 === "string"){
if(func1(data2) > 8000){
const err7 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err8 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err9 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data3.version === undefined){
const err10 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data3.digest === undefined){
const err11 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err12 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err13 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(func1(data4) < 1){
const err14 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err15 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err16 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err17 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err18 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
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
const err19 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err21 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err22 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.completion_criteria !== undefined){
let data7 = data.completion_criteria;
if(Array.isArray(data7)){
if(data7.length > 20){
const err23 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(typeof data8 === "string"){
if(func1(data8) > 1000){
const err24 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/maxLength",keyword:"maxLength",params:{limit: 1000},message:"must NOT have more than 1000 characters"};
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
const err25 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data9 = data.supplemental_hints;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err27 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data.reference_ids !== undefined){
let data10 = data.reference_ids;
if(Array.isArray(data10)){
if(data10.length > 20){
const err29 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
const len1 = data10.length;
for(let i1=0; i1<len1; i1++){
let data11 = data10[i1];
if(typeof data11 === "string"){
if(!(formats0.test(data11))){
const err30 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/reference_ids/" + i1,schemaPath:"#/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/reference_ids",schemaPath:"#/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.model_profile_version_id !== undefined){
let data12 = data.model_profile_version_id;
const _errs33 = errors;
let valid8 = false;
const _errs34 = errors;
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid8 = valid8 || _valid1;
const _errs36 = errors;
if(data12 !== null){
const err35 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid8 = valid8 || _valid1;
if(!valid8){
const err36 = {instancePath:instancePath+"/model_profile_version_id",schemaPath:"#/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
if(data.runtime_profile_version_id !== undefined){
let data13 = data.runtime_profile_version_id;
const _errs39 = errors;
let valid9 = false;
const _errs40 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err37 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
else {
const err38 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs40 === errors;
valid9 = valid9 || _valid2;
const _errs42 = errors;
if(data13 !== null){
const err39 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs42 === errors;
valid9 = valid9 || _valid2;
if(!valid9){
const err40 = {instancePath:instancePath+"/runtime_profile_version_id",schemaPath:"#/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs39;
if(vErrors !== null){
if(_errs39){
vErrors.length = _errs39;
}
else {
vErrors = null;
}
}
}
}
if(data.budget_usd !== undefined){
let data14 = data.budget_usd;
const _errs45 = errors;
let valid10 = false;
const _errs46 = errors;
if(typeof data14 === "string"){
if(!pattern10.test(data14)){
const err41 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid10 = valid10 || _valid3;
const _errs48 = errors;
if(data14 !== null){
const err43 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs48 === errors;
valid10 = valid10 || _valid3;
if(!valid10){
const err44 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
else {
errors = _errs45;
if(vErrors !== null){
if(_errs45){
vErrors.length = _errs45;
}
else {
vErrors = null;
}
}
}
}
if(data.scenario !== undefined){
let data15 = data.scenario;
if(typeof data15 !== "string"){
const err45 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if("code_audit" !== data15){
const err46 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "code_audit"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.repository_url !== undefined){
let data16 = data.repository_url;
const _errs53 = errors;
let valid11 = false;
const _errs54 = errors;
if(typeof data16 === "string"){
if(func1(data16) > 2048){
const err47 = {instancePath:instancePath+"/repository_url",schemaPath:"#/properties/repository_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/repository_url",schemaPath:"#/properties/repository_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
var _valid4 = _errs54 === errors;
valid11 = valid11 || _valid4;
const _errs56 = errors;
if(data16 !== null){
const err49 = {instancePath:instancePath+"/repository_url",schemaPath:"#/properties/repository_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
var _valid4 = _errs56 === errors;
valid11 = valid11 || _valid4;
if(!valid11){
const err50 = {instancePath:instancePath+"/repository_url",schemaPath:"#/properties/repository_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
else {
errors = _errs53;
if(vErrors !== null){
if(_errs53){
vErrors.length = _errs53;
}
else {
vErrors = null;
}
}
}
}
if(data.source_reference_id !== undefined){
let data17 = data.source_reference_id;
const _errs59 = errors;
let valid12 = false;
const _errs60 = errors;
if(typeof data17 === "string"){
if(!(formats0.test(data17))){
const err51 = {instancePath:instancePath+"/source_reference_id",schemaPath:"#/properties/source_reference_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
else {
const err52 = {instancePath:instancePath+"/source_reference_id",schemaPath:"#/properties/source_reference_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
var _valid5 = _errs60 === errors;
valid12 = valid12 || _valid5;
const _errs62 = errors;
if(data17 !== null){
const err53 = {instancePath:instancePath+"/source_reference_id",schemaPath:"#/properties/source_reference_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
var _valid5 = _errs62 === errors;
valid12 = valid12 || _valid5;
if(!valid12){
const err54 = {instancePath:instancePath+"/source_reference_id",schemaPath:"#/properties/source_reference_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
else {
errors = _errs59;
if(vErrors !== null){
if(_errs59){
vErrors.length = _errs59;
}
else {
vErrors = null;
}
}
}
}
if(data.revision !== undefined){
let data18 = data.revision;
const _errs65 = errors;
let valid13 = false;
const _errs66 = errors;
if(typeof data18 === "string"){
if(func1(data18) > 255){
const err55 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
}
else {
const err56 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
var _valid6 = _errs66 === errors;
valid13 = valid13 || _valid6;
const _errs68 = errors;
if(data18 !== null){
const err57 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
var _valid6 = _errs68 === errors;
valid13 = valid13 || _valid6;
if(!valid13){
const err58 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
else {
errors = _errs65;
if(vErrors !== null){
if(_errs65){
vErrors.length = _errs65;
}
else {
vErrors = null;
}
}
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
validate54.errors = vErrors;
return errors === 0;
}
validate54.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

const schema70 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"definition_id":{"format":"uuid","title":"Definition Id","type":"string"},"number":{"minimum":1,"title":"Number","type":"integer"},"name":{"title":"Name","type":"string"},"state_revision":{"minimum":1,"title":"State Revision","type":"integer"},"config":{"$ref":"urn:wuji:contracts:0.5#/$defs/ProfileConfig"}},"required":["id","definition_id","number","name","state_revision","config"],"title":"SelectedModelSnapshot","type":"object"};
const schema71 = {"additionalProperties":false,"properties":{"service_version_id":{"format":"uuid","title":"Service Version Id","type":"string"},"model_id":{"maxLength":255,"minLength":1,"pattern":"^[A-Za-z0-9][A-Za-z0-9_.:-]*$","title":"Model Id","type":"string"},"context_window":{"anyOf":[{"maximum":9007199254740991,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"title":"Context Window"},"max_output_tokens":{"anyOf":[{"maximum":9007199254740991,"minimum":1,"type":"integer"},{"type":"null"}],"default":null,"title":"Max Output Tokens"},"timeout_seconds":{"default":30,"maximum":60,"minimum":1,"title":"Timeout Seconds","type":"integer"},"pricing":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/ModelPricing"},{"type":"null"}],"default":null}},"required":["service_version_id","model_id"],"title":"ProfileConfig","type":"object"};
const schema72 = {"additionalProperties":false,"properties":{"source":{"maxLength":500,"minLength":1,"title":"Source","type":"string"},"input_per_million":{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$","title":"Input Per Million","type":"string"},"output_per_million":{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$","title":"Output Per Million","type":"string"},"cache_mode":{"enum":["standard_input","separate"],"title":"Cache Mode","type":"string"},"cache_read_per_million":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$","type":"string"},{"type":"null"}],"default":null,"title":"Cache Read Per Million"},"cache_creation_per_million":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$","type":"string"},{"type":"null"}],"default":null,"title":"Cache Creation Per Million"}},"required":["source","input_per_million","output_per_million","cache_mode"],"title":"ModelPricing","type":"object"};
const pattern20 = new RegExp("^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "u");
const pattern21 = new RegExp("^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$", "u");

function validate58(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate58.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.service_version_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "service_version_id"},message:"must have required property '"+"service_version_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.model_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "model_id"},message:"must have required property '"+"model_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((((((key0 === "service_version_id") || (key0 === "model_id")) || (key0 === "context_window")) || (key0 === "max_output_tokens")) || (key0 === "timeout_seconds")) || (key0 === "pricing"))){
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
if(data.service_version_id !== undefined){
let data0 = data.service_version_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err3 = {instancePath:instancePath+"/service_version_id",schemaPath:"#/properties/service_version_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err4 = {instancePath:instancePath+"/service_version_id",schemaPath:"#/properties/service_version_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
}
if(data.model_id !== undefined){
let data1 = data.model_id;
if(typeof data1 === "string"){
if(func1(data1) > 255){
const err5 = {instancePath:instancePath+"/model_id",schemaPath:"#/properties/model_id/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(func1(data1) < 1){
const err6 = {instancePath:instancePath+"/model_id",schemaPath:"#/properties/model_id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(!pattern20.test(data1)){
const err7 = {instancePath:instancePath+"/model_id",schemaPath:"#/properties/model_id/pattern",keyword:"pattern",params:{pattern: "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"},message:"must match pattern \""+"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"+"\""};
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
const err8 = {instancePath:instancePath+"/model_id",schemaPath:"#/properties/model_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.context_window !== undefined){
let data2 = data.context_window;
const _errs7 = errors;
let valid1 = false;
const _errs8 = errors;
if(!(((typeof data2 == "number") && (!(data2 % 1) && !isNaN(data2))) && (isFinite(data2)))){
const err9 = {instancePath:instancePath+"/context_window",schemaPath:"#/properties/context_window/anyOf/0/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if((typeof data2 == "number") && (isFinite(data2))){
if(data2 > 9007199254740991 || isNaN(data2)){
const err10 = {instancePath:instancePath+"/context_window",schemaPath:"#/properties/context_window/anyOf/0/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data2 < 1 || isNaN(data2)){
const err11 = {instancePath:instancePath+"/context_window",schemaPath:"#/properties/context_window/anyOf/0/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
var _valid0 = _errs8 === errors;
valid1 = valid1 || _valid0;
const _errs10 = errors;
if(data2 !== null){
const err12 = {instancePath:instancePath+"/context_window",schemaPath:"#/properties/context_window/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err13 = {instancePath:instancePath+"/context_window",schemaPath:"#/properties/context_window/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
else {
errors = _errs7;
if(vErrors !== null){
if(_errs7){
vErrors.length = _errs7;
}
else {
vErrors = null;
}
}
}
}
if(data.max_output_tokens !== undefined){
let data3 = data.max_output_tokens;
const _errs13 = errors;
let valid2 = false;
const _errs14 = errors;
if(!(((typeof data3 == "number") && (!(data3 % 1) && !isNaN(data3))) && (isFinite(data3)))){
const err14 = {instancePath:instancePath+"/max_output_tokens",schemaPath:"#/properties/max_output_tokens/anyOf/0/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if((typeof data3 == "number") && (isFinite(data3))){
if(data3 > 9007199254740991 || isNaN(data3)){
const err15 = {instancePath:instancePath+"/max_output_tokens",schemaPath:"#/properties/max_output_tokens/anyOf/0/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(data3 < 1 || isNaN(data3)){
const err16 = {instancePath:instancePath+"/max_output_tokens",schemaPath:"#/properties/max_output_tokens/anyOf/0/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
var _valid1 = _errs14 === errors;
valid2 = valid2 || _valid1;
const _errs16 = errors;
if(data3 !== null){
const err17 = {instancePath:instancePath+"/max_output_tokens",schemaPath:"#/properties/max_output_tokens/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid1 = _errs16 === errors;
valid2 = valid2 || _valid1;
if(!valid2){
const err18 = {instancePath:instancePath+"/max_output_tokens",schemaPath:"#/properties/max_output_tokens/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
else {
errors = _errs13;
if(vErrors !== null){
if(_errs13){
vErrors.length = _errs13;
}
else {
vErrors = null;
}
}
}
}
if(data.timeout_seconds !== undefined){
let data4 = data.timeout_seconds;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err19 = {instancePath:instancePath+"/timeout_seconds",schemaPath:"#/properties/timeout_seconds/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 60 || isNaN(data4)){
const err20 = {instancePath:instancePath+"/timeout_seconds",schemaPath:"#/properties/timeout_seconds/maximum",keyword:"maximum",params:{comparison: "<=", limit: 60},message:"must be <= 60"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err21 = {instancePath:instancePath+"/timeout_seconds",schemaPath:"#/properties/timeout_seconds/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data.pricing !== undefined){
let data5 = data.pricing;
const _errs21 = errors;
let valid3 = false;
const _errs22 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.source === undefined){
const err22 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/required",keyword:"required",params:{missingProperty: "source"},message:"must have required property '"+"source"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data5.input_per_million === undefined){
const err23 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/required",keyword:"required",params:{missingProperty: "input_per_million"},message:"must have required property '"+"input_per_million"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
if(data5.output_per_million === undefined){
const err24 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/required",keyword:"required",params:{missingProperty: "output_per_million"},message:"must have required property '"+"output_per_million"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if(data5.cache_mode === undefined){
const err25 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/required",keyword:"required",params:{missingProperty: "cache_mode"},message:"must have required property '"+"cache_mode"+"'"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
for(const key1 in data5){
if(!((((((key1 === "source") || (key1 === "input_per_million")) || (key1 === "output_per_million")) || (key1 === "cache_mode")) || (key1 === "cache_read_per_million")) || (key1 === "cache_creation_per_million"))){
const err26 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data5.source !== undefined){
let data6 = data5.source;
if(typeof data6 === "string"){
if(func1(data6) > 500){
const err27 = {instancePath:instancePath+"/pricing/source",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/source/maxLength",keyword:"maxLength",params:{limit: 500},message:"must NOT have more than 500 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
if(func1(data6) < 1){
const err28 = {instancePath:instancePath+"/pricing/source",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/source/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/pricing/source",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/source/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data5.input_per_million !== undefined){
let data7 = data5.input_per_million;
if(typeof data7 === "string"){
if(!pattern21.test(data7)){
const err30 = {instancePath:instancePath+"/pricing/input_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/input_per_million/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/pricing/input_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/input_per_million/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data5.output_per_million !== undefined){
let data8 = data5.output_per_million;
if(typeof data8 === "string"){
if(!pattern21.test(data8)){
const err32 = {instancePath:instancePath+"/pricing/output_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/output_per_million/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"+"\""};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
else {
const err33 = {instancePath:instancePath+"/pricing/output_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/output_per_million/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
if(data5.cache_mode !== undefined){
let data9 = data5.cache_mode;
if(typeof data9 !== "string"){
const err34 = {instancePath:instancePath+"/pricing/cache_mode",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_mode/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(!((data9 === "standard_input") || (data9 === "separate"))){
const err35 = {instancePath:instancePath+"/pricing/cache_mode",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_mode/enum",keyword:"enum",params:{allowedValues: schema72.properties.cache_mode.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
if(data5.cache_read_per_million !== undefined){
let data10 = data5.cache_read_per_million;
const _errs35 = errors;
let valid6 = false;
const _errs36 = errors;
if(typeof data10 === "string"){
if(!pattern21.test(data10)){
const err36 = {instancePath:instancePath+"/pricing/cache_read_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_read_per_million/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"+"\""};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
else {
const err37 = {instancePath:instancePath+"/pricing/cache_read_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_read_per_million/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
var _valid3 = _errs36 === errors;
valid6 = valid6 || _valid3;
const _errs38 = errors;
if(data10 !== null){
const err38 = {instancePath:instancePath+"/pricing/cache_read_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_read_per_million/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid3 = _errs38 === errors;
valid6 = valid6 || _valid3;
if(!valid6){
const err39 = {instancePath:instancePath+"/pricing/cache_read_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_read_per_million/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
else {
errors = _errs35;
if(vErrors !== null){
if(_errs35){
vErrors.length = _errs35;
}
else {
vErrors = null;
}
}
}
}
if(data5.cache_creation_per_million !== undefined){
let data11 = data5.cache_creation_per_million;
const _errs41 = errors;
let valid7 = false;
const _errs42 = errors;
if(typeof data11 === "string"){
if(!pattern21.test(data11)){
const err40 = {instancePath:instancePath+"/pricing/cache_creation_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_creation_per_million/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,12})?$"+"\""};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
else {
const err41 = {instancePath:instancePath+"/pricing/cache_creation_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_creation_per_million/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
var _valid4 = _errs42 === errors;
valid7 = valid7 || _valid4;
const _errs44 = errors;
if(data11 !== null){
const err42 = {instancePath:instancePath+"/pricing/cache_creation_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_creation_per_million/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid4 = _errs44 === errors;
valid7 = valid7 || _valid4;
if(!valid7){
const err43 = {instancePath:instancePath+"/pricing/cache_creation_per_million",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/properties/cache_creation_per_million/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
else {
errors = _errs41;
if(vErrors !== null){
if(_errs41){
vErrors.length = _errs41;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err44 = {instancePath:instancePath+"/pricing",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelPricing/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
var _valid2 = _errs22 === errors;
valid3 = valid3 || _valid2;
const _errs46 = errors;
if(data5 !== null){
const err45 = {instancePath:instancePath+"/pricing",schemaPath:"#/properties/pricing/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
var _valid2 = _errs46 === errors;
valid3 = valid3 || _valid2;
if(!valid3){
const err46 = {instancePath:instancePath+"/pricing",schemaPath:"#/properties/pricing/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
else {
errors = _errs21;
if(vErrors !== null){
if(_errs21){
vErrors.length = _errs21;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err47 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
validate58.errors = vErrors;
return errors === 0;
}
validate58.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate57(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate57.evaluated;
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
if(data.definition_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "definition_id"},message:"must have required property '"+"definition_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.number === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "number"},message:"must have required property '"+"number"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.name === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.state_revision === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state_revision"},message:"must have required property '"+"state_revision"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.config === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "config"},message:"must have required property '"+"config"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
for(const key0 in data){
if(!((((((key0 === "id") || (key0 === "definition_id")) || (key0 === "number")) || (key0 === "name")) || (key0 === "state_revision")) || (key0 === "config"))){
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
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err7 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err8 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.definition_id !== undefined){
let data1 = data.definition_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err9 = {instancePath:instancePath+"/definition_id",schemaPath:"#/properties/definition_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err10 = {instancePath:instancePath+"/definition_id",schemaPath:"#/properties/definition_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.number !== undefined){
let data2 = data.number;
if(!(((typeof data2 == "number") && (!(data2 % 1) && !isNaN(data2))) && (isFinite(data2)))){
const err11 = {instancePath:instancePath+"/number",schemaPath:"#/properties/number/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if((typeof data2 == "number") && (isFinite(data2))){
if(data2 < 1 || isNaN(data2)){
const err12 = {instancePath:instancePath+"/number",schemaPath:"#/properties/number/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
}
if(data.name !== undefined){
if(typeof data.name !== "string"){
const err13 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.state_revision !== undefined){
let data4 = data.state_revision;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err14 = {instancePath:instancePath+"/state_revision",schemaPath:"#/properties/state_revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 < 1 || isNaN(data4)){
const err15 = {instancePath:instancePath+"/state_revision",schemaPath:"#/properties/state_revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data.config !== undefined){
if(!(validate58(data.config, {instancePath:instancePath+"/config",parentData:data,parentDataProperty:"config",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate58.errors : vErrors.concat(validate58.errors);
errors = vErrors.length;
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
validate57.errors = vErrors;
return errors === 0;
}
validate57.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate39(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate39.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.scenario === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.goal_template === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "goal_template"},message:"must have required property '"+"goal_template"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.objective === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "objective"},message:"must have required property '"+"objective"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.completion_criteria === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "completion_criteria"},message:"must have required property '"+"completion_criteria"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.supplemental_hints === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "supplemental_hints"},message:"must have required property '"+"supplemental_hints"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.actual_input === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "actual_input"},message:"must have required property '"+"actual_input"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.authorization === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "authorization"},message:"must have required property '"+"authorization"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.authorization_id === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "authorization_id"},message:"must have required property '"+"authorization_id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.authorization_digest === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "authorization_digest"},message:"must have required property '"+"authorization_digest"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.model === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "model"},message:"must have required property '"+"model"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data.budget_usd === undefined){
const err12 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "budget_usd"},message:"must have required property '"+"budget_usd"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data.created_by === undefined){
const err13 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_by"},message:"must have required property '"+"created_by"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data.created_at === undefined){
const err14 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data.digest === undefined){
const err15 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema53.properties, key0))){
const err16 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err17 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if("1.0" !== data0){
const err18 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.id !== undefined){
let data1 = data.id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err19 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err20 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.scenario !== undefined){
let data2 = data.scenario;
if(typeof data2 !== "string"){
const err21 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if("web_single" !== data2){
const err22 = {instancePath:instancePath+"/scenario",schemaPath:"#/properties/scenario/const",keyword:"const",params:{allowedValue: "web_single"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data.goal_template !== undefined){
let data3 = data.goal_template;
const _errs9 = errors;
let valid1 = false;
const _errs10 = errors;
if(data3 && typeof data3 == "object" && !Array.isArray(data3)){
if(data3.id === undefined){
const err23 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
if(data3.version === undefined){
const err24 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if(data3.digest === undefined){
const err25 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
for(const key1 in data3){
if(!(((key1 === "id") || (key1 === "version")) || (key1 === "digest"))){
const err26 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data3.id !== undefined){
let data4 = data3.id;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err27 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
if(func1(data4) < 1){
const err28 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/goal_template/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data3.version !== undefined){
let data5 = data3.version;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err30 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err31 = {instancePath:instancePath+"/goal_template/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data3.digest !== undefined){
let data6 = data3.digest;
if(typeof data6 === "string"){
if(!pattern6.test(data6)){
const err32 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
else {
const err33 = {instancePath:instancePath+"/goal_template/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err34 = {instancePath:instancePath+"/goal_template",schemaPath:"urn:wuji:contracts:0.5#/$defs/GoalTemplateReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid0 = _errs10 === errors;
valid1 = valid1 || _valid0;
const _errs20 = errors;
if(data3 !== null){
const err35 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err36 = {instancePath:instancePath+"/goal_template",schemaPath:"#/properties/goal_template/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
if(data.objective !== undefined){
let data7 = data.objective;
if(typeof data7 === "string"){
if(func1(data7) > 8000){
const err37 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(func1(data7) < 1){
const err38 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
else {
const err39 = {instancePath:instancePath+"/objective",schemaPath:"#/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
if(data.completion_criteria !== undefined){
let data8 = data.completion_criteria;
if(Array.isArray(data8)){
if(data8.length > 20){
const err40 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
if(data8.length < 1){
const err41 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/minItems",keyword:"minItems",params:{limit: 1},message:"must NOT have fewer than 1 items"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
const len0 = data8.length;
for(let i0=0; i0<len0; i0++){
if(typeof data8[i0] !== "string"){
const err42 = {instancePath:instancePath+"/completion_criteria/" + i0,schemaPath:"#/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err43 = {instancePath:instancePath+"/completion_criteria",schemaPath:"#/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
if(data.supplemental_hints !== undefined){
let data10 = data.supplemental_hints;
if(typeof data10 === "string"){
if(func1(data10) > 8000){
const err44 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err45 = {instancePath:instancePath+"/supplemental_hints",schemaPath:"#/properties/supplemental_hints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
if(data.actual_input !== undefined){
let data11 = data.actual_input;
const _errs31 = errors;
let valid6 = false;
let passing0 = null;
const _errs32 = errors;
if(!(validate40(data11, {instancePath:instancePath+"/actual_input",parentData:data,parentDataProperty:"actual_input",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate40.errors : vErrors.concat(validate40.errors);
errors = vErrors.length;
}
var _valid1 = _errs32 === errors;
if(_valid1){
valid6 = true;
passing0 = 0;
var props1 = true;
}
const _errs33 = errors;
if(!(validate42(data11, {instancePath:instancePath+"/actual_input",parentData:data,parentDataProperty:"actual_input",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate42.errors : vErrors.concat(validate42.errors);
errors = vErrors.length;
}
var _valid1 = _errs33 === errors;
if(_valid1 && valid6){
valid6 = false;
passing0 = [passing0, 1];
}
else {
if(_valid1){
valid6 = true;
passing0 = 1;
if(props1 !== true){
props1 = true;
}
}
const _errs34 = errors;
if(!(validate50(data11, {instancePath:instancePath+"/actual_input",parentData:data,parentDataProperty:"actual_input",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate50.errors : vErrors.concat(validate50.errors);
errors = vErrors.length;
}
var _valid1 = _errs34 === errors;
if(_valid1 && valid6){
valid6 = false;
passing0 = [passing0, 2];
}
else {
if(_valid1){
valid6 = true;
passing0 = 2;
if(props1 !== true){
props1 = true;
}
}
const _errs35 = errors;
if(!(validate52(data11, {instancePath:instancePath+"/actual_input",parentData:data,parentDataProperty:"actual_input",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate52.errors : vErrors.concat(validate52.errors);
errors = vErrors.length;
}
var _valid1 = _errs35 === errors;
if(_valid1 && valid6){
valid6 = false;
passing0 = [passing0, 3];
}
else {
if(_valid1){
valid6 = true;
passing0 = 3;
if(props1 !== true){
props1 = true;
}
}
const _errs36 = errors;
if(!(validate54(data11, {instancePath:instancePath+"/actual_input",parentData:data,parentDataProperty:"actual_input",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate54.errors : vErrors.concat(validate54.errors);
errors = vErrors.length;
}
var _valid1 = _errs36 === errors;
if(_valid1 && valid6){
valid6 = false;
passing0 = [passing0, 4];
}
else {
if(_valid1){
valid6 = true;
passing0 = 4;
if(props1 !== true){
props1 = true;
}
}
}
}
}
}
if(!valid6){
const err46 = {instancePath:instancePath+"/actual_input",schemaPath:"#/properties/actual_input/oneOf",keyword:"oneOf",params:{passingSchemas: passing0},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
else {
errors = _errs31;
if(vErrors !== null){
if(_errs31){
vErrors.length = _errs31;
}
else {
vErrors = null;
}
}
}
}
if(data.authorization !== undefined){
if(!(validate43(data.authorization, {instancePath:instancePath+"/authorization",parentData:data,parentDataProperty:"authorization",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate43.errors : vErrors.concat(validate43.errors);
errors = vErrors.length;
}
}
if(data.authorization_id !== undefined){
let data13 = data.authorization_id;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err47 = {instancePath:instancePath+"/authorization_id",schemaPath:"#/properties/authorization_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/authorization_id",schemaPath:"#/properties/authorization_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data.authorization_digest !== undefined){
let data14 = data.authorization_digest;
if(typeof data14 === "string"){
if(!pattern6.test(data14)){
const err49 = {instancePath:instancePath+"/authorization_digest",schemaPath:"#/properties/authorization_digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
else {
const err50 = {instancePath:instancePath+"/authorization_digest",schemaPath:"#/properties/authorization_digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
if(data.model !== undefined){
if(!(validate57(data.model, {instancePath:instancePath+"/model",parentData:data,parentDataProperty:"model",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate57.errors : vErrors.concat(validate57.errors);
errors = vErrors.length;
}
}
if(data.budget_usd !== undefined){
if(typeof data.budget_usd !== "string"){
const err51 = {instancePath:instancePath+"/budget_usd",schemaPath:"#/properties/budget_usd/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
if(data.created_by !== undefined){
let data17 = data.created_by;
if(typeof data17 === "string"){
if(!(formats0.test(data17))){
const err52 = {instancePath:instancePath+"/created_by",schemaPath:"#/properties/created_by/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
else {
const err53 = {instancePath:instancePath+"/created_by",schemaPath:"#/properties/created_by/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
if(data.created_at !== undefined){
let data18 = data.created_at;
if(typeof data18 === "string"){
if(!(formats2.validate(data18))){
const err54 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
else {
const err55 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
}
if(data.digest !== undefined){
let data19 = data.digest;
if(typeof data19 === "string"){
if(!pattern6.test(data19)){
const err56 = {instancePath:instancePath+"/digest",schemaPath:"#/properties/digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
}
else {
const err57 = {instancePath:instancePath+"/digest",schemaPath:"#/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err58 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
validate39.errors = vErrors;
return errors === 0;
}
validate39.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate38(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate38.evaluated;
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
if(data.project_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.name === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.target_url === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.scope === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "scope"},message:"must have required property '"+"scope"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.version === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.state === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.cleanup_state === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cleanup_state"},message:"must have required property '"+"cleanup_state"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.execution === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "execution"},message:"must have required property '"+"execution"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.allowed_actions === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "allowed_actions"},message:"must have required property '"+"allowed_actions"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.assessment_outcome === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "assessment_outcome"},message:"must have required property '"+"assessment_outcome"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data.stop_reason === undefined){
const err12 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "stop_reason"},message:"must have required property '"+"stop_reason"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data.creation_config === undefined){
const err13 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "creation_config"},message:"must have required property '"+"creation_config"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data.created_at === undefined){
const err14 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data.updated_at === undefined){
const err15 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema50.properties, key0))){
const err16 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.task_kind !== undefined){
let data0 = data.task_kind;
if(typeof data0 !== "string"){
const err17 = {instancePath:instancePath+"/task_kind",schemaPath:"#/properties/task_kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if("web_assessment" !== data0){
const err18 = {instancePath:instancePath+"/task_kind",schemaPath:"#/properties/task_kind/const",keyword:"const",params:{allowedValue: "web_assessment"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.id !== undefined){
let data1 = data.id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err19 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err20 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data2 = data.tenant_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err21 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err22 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data.project_id !== undefined){
let data3 = data.project_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err23 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
else {
const err24 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data.name !== undefined){
let data4 = data.name;
if(typeof data4 === "string"){
if(func1(data4) > 120){
const err25 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(func1(data4) < 1){
const err26 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err27 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data.target_url !== undefined){
let data5 = data.target_url;
if(typeof data5 === "string"){
if(func1(data5) > 2048){
const err28 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(func1(data5) < 1){
const err29 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err30 = {instancePath:instancePath+"/target_url",schemaPath:"#/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data.scope !== undefined){
let data6 = data.scope;
if(data6 && typeof data6 == "object" && !Array.isArray(data6)){
if(data6.authorization_id === undefined){
const err31 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/required",keyword:"required",params:{missingProperty: "authorization_id"},message:"must have required property '"+"authorization_id"+"'"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if(data6.version === undefined){
const err32 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
if(data6.hash === undefined){
const err33 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/required",keyword:"required",params:{missingProperty: "hash"},message:"must have required property '"+"hash"+"'"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
for(const key1 in data6){
if(!(((key1 === "authorization_id") || (key1 === "version")) || (key1 === "hash"))){
const err34 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
if(data6.authorization_id !== undefined){
let data7 = data6.authorization_id;
if(typeof data7 === "string"){
if(!(formats0.test(data7))){
const err35 = {instancePath:instancePath+"/scope/authorization_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/authorization_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
else {
const err36 = {instancePath:instancePath+"/scope/authorization_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/authorization_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
if(data6.version !== undefined){
let data8 = data6.version;
if(!(((typeof data8 == "number") && (!(data8 % 1) && !isNaN(data8))) && (isFinite(data8)))){
const err37 = {instancePath:instancePath+"/scope/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if((typeof data8 == "number") && (isFinite(data8))){
if(data8 < 1 || isNaN(data8)){
const err38 = {instancePath:instancePath+"/scope/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
}
if(data6.hash !== undefined){
let data9 = data6.hash;
if(typeof data9 === "string"){
if(!pattern6.test(data9)){
const err39 = {instancePath:instancePath+"/scope/hash",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/hash/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
else {
const err40 = {instancePath:instancePath+"/scope/hash",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/properties/hash/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
}
else {
const err41 = {instancePath:instancePath+"/scope",schemaPath:"urn:wuji:contracts:0.5#/$defs/TaskAuthorizationBindingResponse/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
if(data.version !== undefined){
let data10 = data.version;
if(!(((typeof data10 == "number") && (!(data10 % 1) && !isNaN(data10))) && (isFinite(data10)))){
const err42 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
if((typeof data10 == "number") && (isFinite(data10))){
if(data10 > 9007199254740991 || isNaN(data10)){
const err43 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(data10 < 1 || isNaN(data10)){
const err44 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
}
}
if(data.state !== undefined){
let data11 = data.state;
if(typeof data11 !== "string"){
const err45 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if(!((((((((data11 === "ready") || (data11 === "provisioning")) || (data11 === "running")) || (data11 === "completing")) || (data11 === "completed")) || (data11 === "cancelling")) || (data11 === "cancelled")) || (data11 === "reconciling"))){
const err46 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema50.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data.cleanup_state !== undefined){
let data12 = data.cleanup_state;
if(typeof data12 !== "string"){
const err47 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if(!((((((data12 === "not_required") || (data12 === "pending")) || (data12 === "running")) || (data12 === "completed")) || (data12 === "failed")) || (data12 === "unknown"))){
const err48 = {instancePath:instancePath+"/cleanup_state",schemaPath:"#/properties/cleanup_state/enum",keyword:"enum",params:{allowedValues: schema50.properties.cleanup_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data.execution !== undefined){
let data13 = data.execution;
if(data13 && typeof data13 == "object" && !Array.isArray(data13)){
if(data13.active_calls === undefined){
const err49 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "active_calls"},message:"must have required property '"+"active_calls"+"'"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
if(data13.unknown_calls === undefined){
const err50 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "unknown_calls"},message:"must have required property '"+"unknown_calls"+"'"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if(data13.egress_state === undefined){
const err51 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/required",keyword:"required",params:{missingProperty: "egress_state"},message:"must have required property '"+"egress_state"+"'"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
for(const key2 in data13){
if(!(((key2 === "active_calls") || (key2 === "unknown_calls")) || (key2 === "egress_state"))){
const err52 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
if(data13.active_calls !== undefined){
let data14 = data13.active_calls;
if(!(((typeof data14 == "number") && (!(data14 % 1) && !isNaN(data14))) && (isFinite(data14)))){
const err53 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/active_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
if((typeof data14 == "number") && (isFinite(data14))){
if(data14 < 0 || isNaN(data14)){
const err54 = {instancePath:instancePath+"/execution/active_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/active_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
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
if(data13.unknown_calls !== undefined){
let data15 = data13.unknown_calls;
if(!(((typeof data15 == "number") && (!(data15 % 1) && !isNaN(data15))) && (isFinite(data15)))){
const err55 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/unknown_calls/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
if((typeof data15 == "number") && (isFinite(data15))){
if(data15 < 0 || isNaN(data15)){
const err56 = {instancePath:instancePath+"/execution/unknown_calls",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/unknown_calls/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
}
}
if(data13.egress_state !== undefined){
let data16 = data13.egress_state;
if(typeof data16 !== "string"){
const err57 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/egress_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
if(!(((((data16 === "not_granted") || (data16 === "fixture_only")) || (data16 === "revoking")) || (data16 === "revoked")) || (data16 === "unknown"))){
const err58 = {instancePath:instancePath+"/execution/egress_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/properties/egress_state/enum",keyword:"enum",params:{allowedValues: schema52.properties.egress_state.enum},message:"must be equal to one of the allowed values"};
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
const err59 = {instancePath:instancePath+"/execution",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebExecutionSummaryResponse/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
}
if(data.allowed_actions !== undefined){
let data17 = data.allowed_actions;
if(Array.isArray(data17)){
if(data17.length > 2){
const err60 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/maxItems",keyword:"maxItems",params:{limit: 2},message:"must NOT have more than 2 items"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
const len0 = data17.length;
for(let i0=0; i0<len0; i0++){
let data18 = data17[i0];
if(typeof data18 !== "string"){
const err61 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"#/properties/allowed_actions/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
if(!((data18 === "start") || (data18 === "cancel"))){
const err62 = {instancePath:instancePath+"/allowed_actions/" + i0,schemaPath:"#/properties/allowed_actions/items/enum",keyword:"enum",params:{allowedValues: schema50.properties.allowed_actions.items.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
}
else {
const err63 = {instancePath:instancePath+"/allowed_actions",schemaPath:"#/properties/allowed_actions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
}
if(data.assessment_outcome !== undefined){
let data19 = data.assessment_outcome;
if(typeof data19 !== "string"){
const err64 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
if(!((((data19 === "not_assessed") || (data19 === "complete")) || (data19 === "partial")) || (data19 === "inconclusive"))){
const err65 = {instancePath:instancePath+"/assessment_outcome",schemaPath:"#/properties/assessment_outcome/enum",keyword:"enum",params:{allowedValues: schema50.properties.assessment_outcome.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
}
if(data.stop_reason !== undefined){
let data20 = data.stop_reason;
const _errs47 = errors;
let valid7 = false;
const _errs48 = errors;
if(typeof data20 !== "string"){
const err66 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
var _valid0 = _errs48 === errors;
valid7 = valid7 || _valid0;
const _errs50 = errors;
if(data20 !== null){
const err67 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
var _valid0 = _errs50 === errors;
valid7 = valid7 || _valid0;
if(!valid7){
const err68 = {instancePath:instancePath+"/stop_reason",schemaPath:"#/properties/stop_reason/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
else {
errors = _errs47;
if(vErrors !== null){
if(_errs47){
vErrors.length = _errs47;
}
else {
vErrors = null;
}
}
}
}
if(data.creation_config !== undefined){
if(!(validate39(data.creation_config, {instancePath:instancePath+"/creation_config",parentData:data,parentDataProperty:"creation_config",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate39.errors : vErrors.concat(validate39.errors);
errors = vErrors.length;
}
}
if(data.start_blockers !== undefined){
let data22 = data.start_blockers;
if(Array.isArray(data22)){
if(data22.length > 20){
const err69 = {instancePath:instancePath+"/start_blockers",schemaPath:"#/properties/start_blockers/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
const len1 = data22.length;
for(let i1=0; i1<len1; i1++){
if(typeof data22[i1] !== "string"){
const err70 = {instancePath:instancePath+"/start_blockers/" + i1,schemaPath:"#/properties/start_blockers/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
}
else {
const err71 = {instancePath:instancePath+"/start_blockers",schemaPath:"#/properties/start_blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
}
if(data.created_at !== undefined){
let data24 = data.created_at;
if(typeof data24 === "string"){
if(!(formats2.validate(data24))){
const err72 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err72];
}
else {
vErrors.push(err72);
}
errors++;
}
}
else {
const err73 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err73];
}
else {
vErrors.push(err73);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data25 = data.updated_at;
if(typeof data25 === "string"){
if(!(formats2.validate(data25))){
const err74 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err74];
}
else {
vErrors.push(err74);
}
errors++;
}
}
else {
const err75 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err75];
}
else {
vErrors.push(err75);
}
errors++;
}
}
}
else {
const err76 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err76];
}
else {
vErrors.push(err76);
}
errors++;
}
validate38.errors = vErrors;
return errors === 0;
}
validate38.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


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
const _errs0 = errors;
let valid0 = false;
let passing0 = null;
const _errs1 = errors;
if(!(validate36(data, {instancePath,parentData,parentDataProperty,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate36.errors : vErrors.concat(validate36.errors);
errors = vErrors.length;
}
var _valid0 = _errs1 === errors;
if(_valid0){
valid0 = true;
passing0 = 0;
var props0 = true;
}
const _errs2 = errors;
if(!(validate38(data, {instancePath,parentData,parentDataProperty,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate38.errors : vErrors.concat(validate38.errors);
errors = vErrors.length;
}
var _valid0 = _errs2 === errors;
if(_valid0 && valid0){
valid0 = false;
passing0 = [passing0, 1];
}
else {
if(_valid0){
valid0 = true;
passing0 = 1;
if(props0 !== true){
props0 = true;
}
}
}
if(!valid0){
const err0 = {instancePath,schemaPath:"#/oneOf",keyword:"oneOf",params:{passingSchemas: passing0},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
else {
errors = _errs0;
if(vErrors !== null){
if(_errs0){
vErrors.length = _errs0;
}
else {
vErrors = null;
}
}
}
validate35.errors = vErrors;
evaluated0.props = props0;
return errors === 0;
}
validate35.evaluated = {"dynamicProps":true,"dynamicItems":false};

export const validateTaskPage = validate63;
const schema73 = {"additionalProperties":false,"properties":{"items":{"items":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/LegacyTask"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebTask"}]},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"TaskPageResponse","type":"object"};

function validate63(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate63.evaluated;
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
let data1 = data0[i0];
const _errs5 = errors;
let valid3 = false;
const _errs6 = errors;
if(!(validate36(data1, {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate36.errors : vErrors.concat(validate36.errors);
errors = vErrors.length;
}
var _valid0 = _errs6 === errors;
valid3 = valid3 || _valid0;
if(_valid0){
var props0 = true;
}
const _errs7 = errors;
if(!(validate38(data1, {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate38.errors : vErrors.concat(validate38.errors);
errors = vErrors.length;
}
var _valid0 = _errs7 === errors;
valid3 = valid3 || _valid0;
if(_valid0){
if(props0 !== true){
props0 = true;
}
}
if(!valid3){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"#/properties/items/items/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
else {
errors = _errs5;
if(vErrors !== null){
if(_errs5){
vErrors.length = _errs5;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err5 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
const _errs9 = errors;
let valid4 = false;
const _errs10 = errors;
if(typeof data2 !== "string"){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
var _valid1 = _errs10 === errors;
valid4 = valid4 || _valid1;
const _errs12 = errors;
if(data2 !== null){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid1 = _errs12 === errors;
valid4 = valid4 || _valid1;
if(!valid4){
const err8 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
else {
errors = _errs9;
if(vErrors !== null){
if(_errs9){
vErrors.length = _errs9;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err9 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
validate63.errors = vErrors;
return errors === 0;
}
validate63.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskSnapshot = validate66;
const schema74 = {"additionalProperties":false,"properties":{"task":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/LegacyTask"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebTask"}],"title":"Task"},"event_cursor":{"maxLength":512,"minLength":1,"title":"Event Cursor","type":"string"}},"required":["task","event_cursor"],"title":"TaskSnapshotResponse","type":"object"};

function validate66(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate66.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.task === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task"},message:"must have required property '"+"task"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.event_cursor === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "event_cursor"},message:"must have required property '"+"event_cursor"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
for(const key0 in data){
if(!((key0 === "task") || (key0 === "event_cursor"))){
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
if(data.task !== undefined){
let data0 = data.task;
const _errs3 = errors;
let valid1 = false;
const _errs4 = errors;
if(!(validate36(data0, {instancePath:instancePath+"/task",parentData:data,parentDataProperty:"task",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate36.errors : vErrors.concat(validate36.errors);
errors = vErrors.length;
}
var _valid0 = _errs4 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
var props0 = true;
}
const _errs5 = errors;
if(!(validate38(data0, {instancePath:instancePath+"/task",parentData:data,parentDataProperty:"task",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate38.errors : vErrors.concat(validate38.errors);
errors = vErrors.length;
}
var _valid0 = _errs5 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
if(props0 !== true){
props0 = true;
}
}
if(!valid1){
const err3 = {instancePath:instancePath+"/task",schemaPath:"#/properties/task/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
else {
errors = _errs3;
if(vErrors !== null){
if(_errs3){
vErrors.length = _errs3;
}
else {
vErrors = null;
}
}
}
}
if(data.event_cursor !== undefined){
let data1 = data.event_cursor;
if(typeof data1 === "string"){
if(func1(data1) > 512){
const err4 = {instancePath:instancePath+"/event_cursor",schemaPath:"#/properties/event_cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(func1(data1) < 1){
const err5 = {instancePath:instancePath+"/event_cursor",schemaPath:"#/properties/event_cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err6 = {instancePath:instancePath+"/event_cursor",schemaPath:"#/properties/event_cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err7 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
validate66.errors = vErrors;
return errors === 0;
}
validate66.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateCommandReceipt = validate69;
const schema75 = {"additionalProperties":false,"properties":{"command_id":{"format":"uuid","title":"Command Id","type":"string"},"idempotency_key":{"format":"uuid","title":"Idempotency Key","type":"string"},"kind":{"enum":["create","start","cancel"],"title":"Kind","type":"string"},"disposition":{"const":"accepted","title":"Disposition","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"task_id":{"format":"uuid","title":"Task Id","type":"string"},"accepted_at":{"format":"date-time","title":"Accepted At","type":"string"},"accepted_task_version":{"maximum":9007199254740991,"minimum":1,"title":"Accepted Task Version","type":"integer"},"request_digest":{"pattern":"^[a-f0-9]{64}$","title":"Request Digest","type":"string"}},"required":["command_id","idempotency_key","kind","disposition","project_id","task_id","accepted_at","accepted_task_version","request_digest"],"title":"CommandReceiptResponse","type":"object"};

function validate69(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate69.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.command_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "command_id"},message:"must have required property '"+"command_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.idempotency_key === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "idempotency_key"},message:"must have required property '"+"idempotency_key"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.kind === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.disposition === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "disposition"},message:"must have required property '"+"disposition"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.project_id === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.task_id === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task_id"},message:"must have required property '"+"task_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.accepted_at === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "accepted_at"},message:"must have required property '"+"accepted_at"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.accepted_task_version === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "accepted_task_version"},message:"must have required property '"+"accepted_task_version"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.request_digest === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "request_digest"},message:"must have required property '"+"request_digest"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema75.properties, key0))){
const err9 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.command_id !== undefined){
let data0 = data.command_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err10 = {instancePath:instancePath+"/command_id",schemaPath:"#/properties/command_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err11 = {instancePath:instancePath+"/command_id",schemaPath:"#/properties/command_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.idempotency_key !== undefined){
let data1 = data.idempotency_key;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err12 = {instancePath:instancePath+"/idempotency_key",schemaPath:"#/properties/idempotency_key/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err13 = {instancePath:instancePath+"/idempotency_key",schemaPath:"#/properties/idempotency_key/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.kind !== undefined){
let data2 = data.kind;
if(typeof data2 !== "string"){
const err14 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(!(((data2 === "create") || (data2 === "start")) || (data2 === "cancel"))){
const err15 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/enum",keyword:"enum",params:{allowedValues: schema75.properties.kind.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.disposition !== undefined){
let data3 = data.disposition;
if(typeof data3 !== "string"){
const err16 = {instancePath:instancePath+"/disposition",schemaPath:"#/properties/disposition/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if("accepted" !== data3){
const err17 = {instancePath:instancePath+"/disposition",schemaPath:"#/properties/disposition/const",keyword:"const",params:{allowedValue: "accepted"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err18 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err19 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.task_id !== undefined){
let data5 = data.task_id;
if(typeof data5 === "string"){
if(!(formats0.test(data5))){
const err20 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err21 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.accepted_at !== undefined){
let data6 = data.accepted_at;
if(typeof data6 === "string"){
if(!(formats2.validate(data6))){
const err22 = {instancePath:instancePath+"/accepted_at",schemaPath:"#/properties/accepted_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
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
const err23 = {instancePath:instancePath+"/accepted_at",schemaPath:"#/properties/accepted_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.accepted_task_version !== undefined){
let data7 = data.accepted_task_version;
if(!(((typeof data7 == "number") && (!(data7 % 1) && !isNaN(data7))) && (isFinite(data7)))){
const err24 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"#/properties/accepted_task_version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 > 9007199254740991 || isNaN(data7)){
const err25 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"#/properties/accepted_task_version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(data7 < 1 || isNaN(data7)){
const err26 = {instancePath:instancePath+"/accepted_task_version",schemaPath:"#/properties/accepted_task_version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
}
if(data.request_digest !== undefined){
let data8 = data.request_digest;
if(typeof data8 === "string"){
if(!pattern6.test(data8)){
const err27 = {instancePath:instancePath+"/request_digest",schemaPath:"#/properties/request_digest/pattern",keyword:"pattern",params:{pattern: "^[a-f0-9]{64}$"},message:"must match pattern \""+"^[a-f0-9]{64}$"+"\""};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/request_digest",schemaPath:"#/properties/request_digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
}
else {
const err29 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
validate69.errors = vErrors;
return errors === 0;
}
validate69.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateEventPage = validate70;
const schema76 = {"type":"object","additionalProperties":false,"required":["items","next_cursor","has_more"],"properties":{"items":{"type":"array","maxItems":100,"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/TaskEvent"}},"next_cursor":{"$ref":"urn:wuji:contracts:0.5#/$defs/Cursor"},"has_more":{"type":"boolean"}}};
const schema78 = {"type":"string","minLength":1,"maxLength":512};
const schema77 = {"type":"object","additionalProperties":false,"required":["schema_version","event_id","cursor","tenant_id","project_id","task_id","aggregate_version","type","occurred_at","trace_id","summary"],"properties":{"schema_version":{"type":"string","const":"1.0"},"event_id":{"type":"string","format":"uuid"},"cursor":{"$ref":"urn:wuji:contracts:0.5#/$defs/Cursor"},"tenant_id":{"type":"string","format":"uuid"},"project_id":{"type":"string","format":"uuid"},"task_id":{"type":"string","format":"uuid"},"aggregate_version":{"$ref":"urn:wuji:contracts:0.5#/$defs/Version"},"type":{"type":"string","enum":["task.changed","task.cleanup_changed","artifact.available"]},"occurred_at":{"type":"string","format":"date-time"},"trace_id":{"type":"string","format":"uuid"},"summary":{"type":"string","minLength":1,"maxLength":500}}};

function validate71(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate71.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.schema_version === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.event_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "event_id"},message:"must have required property '"+"event_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.cursor === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cursor"},message:"must have required property '"+"cursor"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.tenant_id === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.project_id === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.task_id === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "task_id"},message:"must have required property '"+"task_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.aggregate_version === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "aggregate_version"},message:"must have required property '"+"aggregate_version"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.type === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "type"},message:"must have required property '"+"type"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.occurred_at === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "occurred_at"},message:"must have required property '"+"occurred_at"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.trace_id === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "trace_id"},message:"must have required property '"+"trace_id"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.summary === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "summary"},message:"must have required property '"+"summary"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema77.properties, key0))){
const err11 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.schema_version !== undefined){
let data0 = data.schema_version;
if(typeof data0 !== "string"){
const err12 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if("1.0" !== data0){
const err13 = {instancePath:instancePath+"/schema_version",schemaPath:"#/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.event_id !== undefined){
let data1 = data.event_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err14 = {instancePath:instancePath+"/event_id",schemaPath:"#/properties/event_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/event_id",schemaPath:"#/properties/event_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.cursor !== undefined){
let data2 = data.cursor;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err16 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(func1(data2) < 1){
const err17 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
else {
const err18 = {instancePath:instancePath+"/cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data3 = data.tenant_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err19 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err20 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.project_id !== undefined){
let data4 = data.project_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err21 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err22 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data.task_id !== undefined){
let data5 = data.task_id;
if(typeof data5 === "string"){
if(!(formats0.test(data5))){
const err23 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
else {
const err24 = {instancePath:instancePath+"/task_id",schemaPath:"#/properties/task_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data.aggregate_version !== undefined){
let data6 = data.aggregate_version;
if(!(((typeof data6 == "number") && (!(data6 % 1) && !isNaN(data6))) && (isFinite(data6)))){
const err25 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if((typeof data6 == "number") && (isFinite(data6))){
if(data6 > 9007199254740991 || isNaN(data6)){
const err26 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data6 < 1 || isNaN(data6)){
const err27 = {instancePath:instancePath+"/aggregate_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/Version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data.type !== undefined){
let data7 = data.type;
if(typeof data7 !== "string"){
const err28 = {instancePath:instancePath+"/type",schemaPath:"#/properties/type/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(!(((data7 === "task.changed") || (data7 === "task.cleanup_changed")) || (data7 === "artifact.available"))){
const err29 = {instancePath:instancePath+"/type",schemaPath:"#/properties/type/enum",keyword:"enum",params:{allowedValues: schema77.properties.type.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data.occurred_at !== undefined){
let data8 = data.occurred_at;
if(typeof data8 === "string"){
if(!(formats2.validate(data8))){
const err30 = {instancePath:instancePath+"/occurred_at",schemaPath:"#/properties/occurred_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/occurred_at",schemaPath:"#/properties/occurred_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data.trace_id !== undefined){
let data9 = data.trace_id;
if(typeof data9 === "string"){
if(!(formats0.test(data9))){
const err32 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
else {
const err33 = {instancePath:instancePath+"/trace_id",schemaPath:"#/properties/trace_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
if(data.summary !== undefined){
let data10 = data.summary;
if(typeof data10 === "string"){
if(func1(data10) > 500){
const err34 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/maxLength",keyword:"maxLength",params:{limit: 500},message:"must NOT have more than 500 characters"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(func1(data10) < 1){
const err35 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
else {
const err36 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err37 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
validate71.errors = vErrors;
return errors === 0;
}
validate71.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate70(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate70.evaluated;
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
if(data.has_more === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "has_more"},message:"must have required property '"+"has_more"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
for(const key0 in data){
if(!(((key0 === "items") || (key0 === "next_cursor")) || (key0 === "has_more"))){
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
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 100){
const err4 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
if(!(validate71(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate71.errors : vErrors.concat(validate71.errors);
errors = vErrors.length;
}
}
}
else {
const err5 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data2 = data.next_cursor;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(func1(data2) < 1){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
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
const err8 = {instancePath:instancePath+"/next_cursor",schemaPath:"urn:wuji:contracts:0.5#/$defs/Cursor/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data.has_more !== undefined){
if(typeof data.has_more !== "boolean"){
const err9 = {instancePath:instancePath+"/has_more",schemaPath:"#/properties/has_more/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
}
else {
const err10 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
validate70.errors = vErrors;
return errors === 0;
}
validate70.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateSavedTaskDraft = validate73;
const schema81 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"tenant_id":{"format":"uuid","title":"Tenant Id","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"user_id":{"format":"uuid","title":"User Id","type":"string"},"version":{"maximum":9007199254740991,"minimum":1,"title":"Version","type":"integer"},"content":{"anyOf":[{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft"}]},{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraftV2"}]}],"title":"Content"},"selected_model_summary":{"anyOf":[{"additionalProperties":true,"type":"object"},{"type":"null"}],"default":null,"title":"Selected Model Summary"},"last_created_task_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Last Created Task Id"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","tenant_id","project_id","user_id","version","content","created_at","updated_at"],"title":"TaskDraftResponse","type":"object"};
const schema82 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"ctf","title":"Scenario","type":"string"},"challenge":{"default":"","maxLength":8000,"title":"Challenge","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"}},"required":["scenario"],"title":"CtfDraft","type":"object"};
const schema83 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"web_single","title":"Scenario","type":"string"},"entry_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Entry Url"},"include_subdomains":{"default":false,"title":"Include Subdomains","type":"boolean"},"additional_origins":{"items":{"maxLength":2048,"type":"string"},"maxItems":100,"title":"Additional Origins","type":"array"}},"required":["scenario"],"title":"WebDraft","type":"object"};
const schema84 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"comprehensive","title":"Scenario","type":"string"},"assets":{"items":{"maxLength":2048,"type":"string"},"maxItems":100,"title":"Assets","type":"array"},"access_notes":{"default":"","maxLength":4000,"title":"Access Notes","type":"string"}},"required":["scenario"],"title":"ComprehensiveDraft","type":"object"};
const schema85 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"exercise","title":"Scenario","type":"string"},"organization_name":{"default":"","maxLength":255,"title":"Organization Name","type":"string"},"known_domains":{"items":{"maxLength":253,"type":"string"},"maxItems":100,"title":"Known Domains","type":"array"}},"required":["scenario"],"title":"ExerciseDraft","type":"object"};
const schema86 = {"additionalProperties":false,"not":{"properties":{"repository_url":{"type":"string"},"source_reference_id":{"type":"string"}},"required":["repository_url","source_reference_id"]},"properties":{"schema_version":{"const":"1.0","default":"1.0","title":"Schema Version","type":"string"},"name":{"default":"","maxLength":120,"title":"Name","type":"string"},"objective":{"default":"","maxLength":8000,"title":"Objective","type":"string"},"starting_point":{"default":"","maxLength":8000,"title":"Starting Point","type":"string"},"constraints":{"default":"","maxLength":4000,"title":"Constraints","type":"string"},"reference_ids":{"items":{"format":"uuid","type":"string"},"maxItems":20,"title":"Reference Ids","type":"array"},"model_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Model Profile Version Id"},"runtime_profile_version_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Runtime Profile Version Id"},"budget_usd":{"anyOf":[{"pattern":"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$","type":"string"},{"type":"null"}],"default":null,"not":{"enum":["0","0.0","0.00","0.000","0.0000","0.00000","0.000000"]},"title":"Budget Usd"},"scenario":{"const":"code_audit","title":"Scenario","type":"string"},"repository_url":{"anyOf":[{"maxLength":2048,"type":"string"},{"type":"null"}],"default":null,"title":"Repository Url"},"source_reference_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Source Reference Id"},"revision":{"anyOf":[{"maxLength":255,"type":"string"},{"type":"null"}],"default":null,"title":"Revision"}},"required":["scenario"],"title":"CodeAuditDraft","type":"object"};

function validate73(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate73.evaluated;
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
if(data.project_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.user_id === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "user_id"},message:"must have required property '"+"user_id"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.version === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.content === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "content"},message:"must have required property '"+"content"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.created_at === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.updated_at === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema81.properties, key0))){
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
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err9 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err10 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err11 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
else {
const err12 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.project_id !== undefined){
let data2 = data.project_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err13 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
else {
const err14 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data.user_id !== undefined){
let data3 = data.user_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err15 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
else {
const err16 = {instancePath:instancePath+"/user_id",schemaPath:"#/properties/user_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.version !== undefined){
let data4 = data.version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err17 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 9007199254740991 || isNaN(data4)){
const err18 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err19 = {instancePath:instancePath+"/version",schemaPath:"#/properties/version/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
if(data.content !== undefined){
let data5 = data.content;
const _errs13 = errors;
let valid1 = false;
const _errs14 = errors;
const _errs15 = errors;
let valid2 = false;
let passing0 = null;
const _errs16 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err20 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
for(const key1 in data5){
if(!(func22.call(schema82.properties, key1))){
const err21 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data6 = data5.schema_version;
if(typeof data6 !== "string"){
const err22 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if("1.0" !== data6){
const err23 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data5.name !== undefined){
let data7 = data5.name;
if(typeof data7 === "string"){
if(func1(data7) > 120){
const err24 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err25 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data5.objective !== undefined){
let data8 = data5.objective;
if(typeof data8 === "string"){
if(func1(data8) > 8000){
const err26 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
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
const err27 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data9 = data5.starting_point;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err28 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data10 = data5.constraints;
if(typeof data10 === "string"){
if(func1(data10) > 4000){
const err30 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data11 = data5.reference_ids;
if(Array.isArray(data11)){
if(data11.length > 20){
const err32 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
const len0 = data11.length;
for(let i0=0; i0<len0; i0++){
let data12 = data11[i0];
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err33 = {instancePath:instancePath+"/content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
}
else {
const err35 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data13 = data5.model_profile_version_id;
const _errs35 = errors;
let valid7 = false;
const _errs36 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err36 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
else {
const err37 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
var _valid2 = _errs36 === errors;
valid7 = valid7 || _valid2;
const _errs38 = errors;
if(data13 !== null){
const err38 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid2 = _errs38 === errors;
valid7 = valid7 || _valid2;
if(!valid7){
const err39 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
else {
errors = _errs35;
if(vErrors !== null){
if(_errs35){
vErrors.length = _errs35;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data14 = data5.runtime_profile_version_id;
const _errs41 = errors;
let valid8 = false;
const _errs42 = errors;
if(typeof data14 === "string"){
if(!(formats0.test(data14))){
const err40 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
else {
const err41 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
var _valid3 = _errs42 === errors;
valid8 = valid8 || _valid3;
const _errs44 = errors;
if(data14 !== null){
const err42 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid3 = _errs44 === errors;
valid8 = valid8 || _valid3;
if(!valid8){
const err43 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
else {
errors = _errs41;
if(vErrors !== null){
if(_errs41){
vErrors.length = _errs41;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data15 = data5.budget_usd;
const _errs47 = errors;
const _errs48 = errors;
if(!(((((((data15 === "0") || (data15 === "0.0")) || (data15 === "0.00")) || (data15 === "0.000")) || (data15 === "0.0000")) || (data15 === "0.00000")) || (data15 === "0.000000"))){
const err44 = {};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
var valid9 = _errs48 === errors;
if(valid9){
const err45 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
else {
errors = _errs47;
if(vErrors !== null){
if(_errs47){
vErrors.length = _errs47;
}
else {
vErrors = null;
}
}
}
const _errs49 = errors;
let valid10 = false;
const _errs50 = errors;
if(typeof data15 === "string"){
if(!pattern10.test(data15)){
const err46 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
else {
const err47 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
var _valid4 = _errs50 === errors;
valid10 = valid10 || _valid4;
const _errs52 = errors;
if(data15 !== null){
const err48 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
var _valid4 = _errs52 === errors;
valid10 = valid10 || _valid4;
if(!valid10){
const err49 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
else {
errors = _errs49;
if(vErrors !== null){
if(_errs49){
vErrors.length = _errs49;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data16 = data5.scenario;
if(typeof data16 !== "string"){
const err50 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
if("ctf" !== data16){
const err51 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "ctf"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
if(data5.challenge !== undefined){
let data17 = data5.challenge;
if(typeof data17 === "string"){
if(func1(data17) > 8000){
const err52 = {instancePath:instancePath+"/content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
else {
const err53 = {instancePath:instancePath+"/content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data18 = data5.entry_url;
const _errs59 = errors;
let valid11 = false;
const _errs60 = errors;
if(typeof data18 === "string"){
if(func1(data18) > 2048){
const err54 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
else {
const err55 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
var _valid5 = _errs60 === errors;
valid11 = valid11 || _valid5;
const _errs62 = errors;
if(data18 !== null){
const err56 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
var _valid5 = _errs62 === errors;
valid11 = valid11 || _valid5;
if(!valid11){
const err57 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
else {
errors = _errs59;
if(vErrors !== null){
if(_errs59){
vErrors.length = _errs59;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err58 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
var _valid1 = _errs16 === errors;
if(_valid1){
valid2 = true;
passing0 = 0;
var props0 = true;
}
const _errs64 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err59 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
for(const key2 in data5){
if(!(func22.call(schema83.properties, key2))){
const err60 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data19 = data5.schema_version;
if(typeof data19 !== "string"){
const err61 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
if("1.0" !== data19){
const err62 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
if(data5.name !== undefined){
let data20 = data5.name;
if(typeof data20 === "string"){
if(func1(data20) > 120){
const err63 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
}
else {
const err64 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
}
if(data5.objective !== undefined){
let data21 = data5.objective;
if(typeof data21 === "string"){
if(func1(data21) > 8000){
const err65 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
}
else {
const err66 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data22 = data5.starting_point;
if(typeof data22 === "string"){
if(func1(data22) > 8000){
const err67 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
}
else {
const err68 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data23 = data5.constraints;
if(typeof data23 === "string"){
if(func1(data23) > 4000){
const err69 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
}
else {
const err70 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data24 = data5.reference_ids;
if(Array.isArray(data24)){
if(data24.length > 20){
const err71 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
const len1 = data24.length;
for(let i1=0; i1<len1; i1++){
let data25 = data24[i1];
if(typeof data25 === "string"){
if(!(formats0.test(data25))){
const err72 = {instancePath:instancePath+"/content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err72];
}
else {
vErrors.push(err72);
}
errors++;
}
}
else {
const err73 = {instancePath:instancePath+"/content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err73];
}
else {
vErrors.push(err73);
}
errors++;
}
}
}
else {
const err74 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err74];
}
else {
vErrors.push(err74);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data26 = data5.model_profile_version_id;
const _errs83 = errors;
let valid16 = false;
const _errs84 = errors;
if(typeof data26 === "string"){
if(!(formats0.test(data26))){
const err75 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err75];
}
else {
vErrors.push(err75);
}
errors++;
}
}
else {
const err76 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err76];
}
else {
vErrors.push(err76);
}
errors++;
}
var _valid6 = _errs84 === errors;
valid16 = valid16 || _valid6;
const _errs86 = errors;
if(data26 !== null){
const err77 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err77];
}
else {
vErrors.push(err77);
}
errors++;
}
var _valid6 = _errs86 === errors;
valid16 = valid16 || _valid6;
if(!valid16){
const err78 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err78];
}
else {
vErrors.push(err78);
}
errors++;
}
else {
errors = _errs83;
if(vErrors !== null){
if(_errs83){
vErrors.length = _errs83;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data27 = data5.runtime_profile_version_id;
const _errs89 = errors;
let valid17 = false;
const _errs90 = errors;
if(typeof data27 === "string"){
if(!(formats0.test(data27))){
const err79 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err79];
}
else {
vErrors.push(err79);
}
errors++;
}
}
else {
const err80 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err80];
}
else {
vErrors.push(err80);
}
errors++;
}
var _valid7 = _errs90 === errors;
valid17 = valid17 || _valid7;
const _errs92 = errors;
if(data27 !== null){
const err81 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err81];
}
else {
vErrors.push(err81);
}
errors++;
}
var _valid7 = _errs92 === errors;
valid17 = valid17 || _valid7;
if(!valid17){
const err82 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err82];
}
else {
vErrors.push(err82);
}
errors++;
}
else {
errors = _errs89;
if(vErrors !== null){
if(_errs89){
vErrors.length = _errs89;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data28 = data5.budget_usd;
const _errs95 = errors;
const _errs96 = errors;
if(!(((((((data28 === "0") || (data28 === "0.0")) || (data28 === "0.00")) || (data28 === "0.000")) || (data28 === "0.0000")) || (data28 === "0.00000")) || (data28 === "0.000000"))){
const err83 = {};
if(vErrors === null){
vErrors = [err83];
}
else {
vErrors.push(err83);
}
errors++;
}
var valid18 = _errs96 === errors;
if(valid18){
const err84 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err84];
}
else {
vErrors.push(err84);
}
errors++;
}
else {
errors = _errs95;
if(vErrors !== null){
if(_errs95){
vErrors.length = _errs95;
}
else {
vErrors = null;
}
}
}
const _errs97 = errors;
let valid19 = false;
const _errs98 = errors;
if(typeof data28 === "string"){
if(!pattern10.test(data28)){
const err85 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err85];
}
else {
vErrors.push(err85);
}
errors++;
}
}
else {
const err86 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err86];
}
else {
vErrors.push(err86);
}
errors++;
}
var _valid8 = _errs98 === errors;
valid19 = valid19 || _valid8;
const _errs100 = errors;
if(data28 !== null){
const err87 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err87];
}
else {
vErrors.push(err87);
}
errors++;
}
var _valid8 = _errs100 === errors;
valid19 = valid19 || _valid8;
if(!valid19){
const err88 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err88];
}
else {
vErrors.push(err88);
}
errors++;
}
else {
errors = _errs97;
if(vErrors !== null){
if(_errs97){
vErrors.length = _errs97;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data29 = data5.scenario;
if(typeof data29 !== "string"){
const err89 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err89];
}
else {
vErrors.push(err89);
}
errors++;
}
if("web_single" !== data29){
const err90 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "web_single"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err90];
}
else {
vErrors.push(err90);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data30 = data5.entry_url;
const _errs105 = errors;
let valid20 = false;
const _errs106 = errors;
if(typeof data30 === "string"){
if(func1(data30) > 2048){
const err91 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err91];
}
else {
vErrors.push(err91);
}
errors++;
}
}
else {
const err92 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err92];
}
else {
vErrors.push(err92);
}
errors++;
}
var _valid9 = _errs106 === errors;
valid20 = valid20 || _valid9;
const _errs108 = errors;
if(data30 !== null){
const err93 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err93];
}
else {
vErrors.push(err93);
}
errors++;
}
var _valid9 = _errs108 === errors;
valid20 = valid20 || _valid9;
if(!valid20){
const err94 = {instancePath:instancePath+"/content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err94];
}
else {
vErrors.push(err94);
}
errors++;
}
else {
errors = _errs105;
if(vErrors !== null){
if(_errs105){
vErrors.length = _errs105;
}
else {
vErrors = null;
}
}
}
}
if(data5.include_subdomains !== undefined){
if(typeof data5.include_subdomains !== "boolean"){
const err95 = {instancePath:instancePath+"/content/include_subdomains",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/include_subdomains/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err95];
}
else {
vErrors.push(err95);
}
errors++;
}
}
if(data5.additional_origins !== undefined){
let data32 = data5.additional_origins;
if(Array.isArray(data32)){
if(data32.length > 100){
const err96 = {instancePath:instancePath+"/content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err96];
}
else {
vErrors.push(err96);
}
errors++;
}
const len2 = data32.length;
for(let i2=0; i2<len2; i2++){
let data33 = data32[i2];
if(typeof data33 === "string"){
if(func1(data33) > 2048){
const err97 = {instancePath:instancePath+"/content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err97];
}
else {
vErrors.push(err97);
}
errors++;
}
}
else {
const err98 = {instancePath:instancePath+"/content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err98];
}
else {
vErrors.push(err98);
}
errors++;
}
}
}
else {
const err99 = {instancePath:instancePath+"/content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err99];
}
else {
vErrors.push(err99);
}
errors++;
}
}
}
else {
const err100 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err100];
}
else {
vErrors.push(err100);
}
errors++;
}
var _valid1 = _errs64 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 1];
}
else {
if(_valid1){
valid2 = true;
passing0 = 1;
if(props0 !== true){
props0 = true;
}
}
const _errs116 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err101 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err101];
}
else {
vErrors.push(err101);
}
errors++;
}
for(const key3 in data5){
if(!(func22.call(schema84.properties, key3))){
const err102 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key3},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err102];
}
else {
vErrors.push(err102);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data34 = data5.schema_version;
if(typeof data34 !== "string"){
const err103 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err103];
}
else {
vErrors.push(err103);
}
errors++;
}
if("1.0" !== data34){
const err104 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err104];
}
else {
vErrors.push(err104);
}
errors++;
}
}
if(data5.name !== undefined){
let data35 = data5.name;
if(typeof data35 === "string"){
if(func1(data35) > 120){
const err105 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err105];
}
else {
vErrors.push(err105);
}
errors++;
}
}
else {
const err106 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err106];
}
else {
vErrors.push(err106);
}
errors++;
}
}
if(data5.objective !== undefined){
let data36 = data5.objective;
if(typeof data36 === "string"){
if(func1(data36) > 8000){
const err107 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err107];
}
else {
vErrors.push(err107);
}
errors++;
}
}
else {
const err108 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err108];
}
else {
vErrors.push(err108);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data37 = data5.starting_point;
if(typeof data37 === "string"){
if(func1(data37) > 8000){
const err109 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err109];
}
else {
vErrors.push(err109);
}
errors++;
}
}
else {
const err110 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err110];
}
else {
vErrors.push(err110);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data38 = data5.constraints;
if(typeof data38 === "string"){
if(func1(data38) > 4000){
const err111 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err111];
}
else {
vErrors.push(err111);
}
errors++;
}
}
else {
const err112 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err112];
}
else {
vErrors.push(err112);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data39 = data5.reference_ids;
if(Array.isArray(data39)){
if(data39.length > 20){
const err113 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err113];
}
else {
vErrors.push(err113);
}
errors++;
}
const len3 = data39.length;
for(let i3=0; i3<len3; i3++){
let data40 = data39[i3];
if(typeof data40 === "string"){
if(!(formats0.test(data40))){
const err114 = {instancePath:instancePath+"/content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err114];
}
else {
vErrors.push(err114);
}
errors++;
}
}
else {
const err115 = {instancePath:instancePath+"/content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err115];
}
else {
vErrors.push(err115);
}
errors++;
}
}
}
else {
const err116 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err116];
}
else {
vErrors.push(err116);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data41 = data5.model_profile_version_id;
const _errs135 = errors;
let valid27 = false;
const _errs136 = errors;
if(typeof data41 === "string"){
if(!(formats0.test(data41))){
const err117 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err117];
}
else {
vErrors.push(err117);
}
errors++;
}
}
else {
const err118 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err118];
}
else {
vErrors.push(err118);
}
errors++;
}
var _valid10 = _errs136 === errors;
valid27 = valid27 || _valid10;
const _errs138 = errors;
if(data41 !== null){
const err119 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err119];
}
else {
vErrors.push(err119);
}
errors++;
}
var _valid10 = _errs138 === errors;
valid27 = valid27 || _valid10;
if(!valid27){
const err120 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err120];
}
else {
vErrors.push(err120);
}
errors++;
}
else {
errors = _errs135;
if(vErrors !== null){
if(_errs135){
vErrors.length = _errs135;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data42 = data5.runtime_profile_version_id;
const _errs141 = errors;
let valid28 = false;
const _errs142 = errors;
if(typeof data42 === "string"){
if(!(formats0.test(data42))){
const err121 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err121];
}
else {
vErrors.push(err121);
}
errors++;
}
}
else {
const err122 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err122];
}
else {
vErrors.push(err122);
}
errors++;
}
var _valid11 = _errs142 === errors;
valid28 = valid28 || _valid11;
const _errs144 = errors;
if(data42 !== null){
const err123 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err123];
}
else {
vErrors.push(err123);
}
errors++;
}
var _valid11 = _errs144 === errors;
valid28 = valid28 || _valid11;
if(!valid28){
const err124 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err124];
}
else {
vErrors.push(err124);
}
errors++;
}
else {
errors = _errs141;
if(vErrors !== null){
if(_errs141){
vErrors.length = _errs141;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data43 = data5.budget_usd;
const _errs147 = errors;
const _errs148 = errors;
if(!(((((((data43 === "0") || (data43 === "0.0")) || (data43 === "0.00")) || (data43 === "0.000")) || (data43 === "0.0000")) || (data43 === "0.00000")) || (data43 === "0.000000"))){
const err125 = {};
if(vErrors === null){
vErrors = [err125];
}
else {
vErrors.push(err125);
}
errors++;
}
var valid29 = _errs148 === errors;
if(valid29){
const err126 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err126];
}
else {
vErrors.push(err126);
}
errors++;
}
else {
errors = _errs147;
if(vErrors !== null){
if(_errs147){
vErrors.length = _errs147;
}
else {
vErrors = null;
}
}
}
const _errs149 = errors;
let valid30 = false;
const _errs150 = errors;
if(typeof data43 === "string"){
if(!pattern10.test(data43)){
const err127 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err127];
}
else {
vErrors.push(err127);
}
errors++;
}
}
else {
const err128 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err128];
}
else {
vErrors.push(err128);
}
errors++;
}
var _valid12 = _errs150 === errors;
valid30 = valid30 || _valid12;
const _errs152 = errors;
if(data43 !== null){
const err129 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err129];
}
else {
vErrors.push(err129);
}
errors++;
}
var _valid12 = _errs152 === errors;
valid30 = valid30 || _valid12;
if(!valid30){
const err130 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err130];
}
else {
vErrors.push(err130);
}
errors++;
}
else {
errors = _errs149;
if(vErrors !== null){
if(_errs149){
vErrors.length = _errs149;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data44 = data5.scenario;
if(typeof data44 !== "string"){
const err131 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err131];
}
else {
vErrors.push(err131);
}
errors++;
}
if("comprehensive" !== data44){
const err132 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "comprehensive"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err132];
}
else {
vErrors.push(err132);
}
errors++;
}
}
if(data5.assets !== undefined){
let data45 = data5.assets;
if(Array.isArray(data45)){
if(data45.length > 100){
const err133 = {instancePath:instancePath+"/content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err133];
}
else {
vErrors.push(err133);
}
errors++;
}
const len4 = data45.length;
for(let i4=0; i4<len4; i4++){
let data46 = data45[i4];
if(typeof data46 === "string"){
if(func1(data46) > 2048){
const err134 = {instancePath:instancePath+"/content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err134];
}
else {
vErrors.push(err134);
}
errors++;
}
}
else {
const err135 = {instancePath:instancePath+"/content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err135];
}
else {
vErrors.push(err135);
}
errors++;
}
}
}
else {
const err136 = {instancePath:instancePath+"/content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err136];
}
else {
vErrors.push(err136);
}
errors++;
}
}
if(data5.access_notes !== undefined){
let data47 = data5.access_notes;
if(typeof data47 === "string"){
if(func1(data47) > 4000){
const err137 = {instancePath:instancePath+"/content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err137];
}
else {
vErrors.push(err137);
}
errors++;
}
}
else {
const err138 = {instancePath:instancePath+"/content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err138];
}
else {
vErrors.push(err138);
}
errors++;
}
}
}
else {
const err139 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err139];
}
else {
vErrors.push(err139);
}
errors++;
}
var _valid1 = _errs116 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 2];
}
else {
if(_valid1){
valid2 = true;
passing0 = 2;
if(props0 !== true){
props0 = true;
}
}
const _errs162 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err140 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err140];
}
else {
vErrors.push(err140);
}
errors++;
}
for(const key4 in data5){
if(!(func22.call(schema85.properties, key4))){
const err141 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key4},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err141];
}
else {
vErrors.push(err141);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data48 = data5.schema_version;
if(typeof data48 !== "string"){
const err142 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err142];
}
else {
vErrors.push(err142);
}
errors++;
}
if("1.0" !== data48){
const err143 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err143];
}
else {
vErrors.push(err143);
}
errors++;
}
}
if(data5.name !== undefined){
let data49 = data5.name;
if(typeof data49 === "string"){
if(func1(data49) > 120){
const err144 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err144];
}
else {
vErrors.push(err144);
}
errors++;
}
}
else {
const err145 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err145];
}
else {
vErrors.push(err145);
}
errors++;
}
}
if(data5.objective !== undefined){
let data50 = data5.objective;
if(typeof data50 === "string"){
if(func1(data50) > 8000){
const err146 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err146];
}
else {
vErrors.push(err146);
}
errors++;
}
}
else {
const err147 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err147];
}
else {
vErrors.push(err147);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data51 = data5.starting_point;
if(typeof data51 === "string"){
if(func1(data51) > 8000){
const err148 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err148];
}
else {
vErrors.push(err148);
}
errors++;
}
}
else {
const err149 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err149];
}
else {
vErrors.push(err149);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data52 = data5.constraints;
if(typeof data52 === "string"){
if(func1(data52) > 4000){
const err150 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err150];
}
else {
vErrors.push(err150);
}
errors++;
}
}
else {
const err151 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err151];
}
else {
vErrors.push(err151);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data53 = data5.reference_ids;
if(Array.isArray(data53)){
if(data53.length > 20){
const err152 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err152];
}
else {
vErrors.push(err152);
}
errors++;
}
const len5 = data53.length;
for(let i5=0; i5<len5; i5++){
let data54 = data53[i5];
if(typeof data54 === "string"){
if(!(formats0.test(data54))){
const err153 = {instancePath:instancePath+"/content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err153];
}
else {
vErrors.push(err153);
}
errors++;
}
}
else {
const err154 = {instancePath:instancePath+"/content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err154];
}
else {
vErrors.push(err154);
}
errors++;
}
}
}
else {
const err155 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err155];
}
else {
vErrors.push(err155);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data55 = data5.model_profile_version_id;
const _errs181 = errors;
let valid37 = false;
const _errs182 = errors;
if(typeof data55 === "string"){
if(!(formats0.test(data55))){
const err156 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err156];
}
else {
vErrors.push(err156);
}
errors++;
}
}
else {
const err157 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err157];
}
else {
vErrors.push(err157);
}
errors++;
}
var _valid13 = _errs182 === errors;
valid37 = valid37 || _valid13;
const _errs184 = errors;
if(data55 !== null){
const err158 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err158];
}
else {
vErrors.push(err158);
}
errors++;
}
var _valid13 = _errs184 === errors;
valid37 = valid37 || _valid13;
if(!valid37){
const err159 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err159];
}
else {
vErrors.push(err159);
}
errors++;
}
else {
errors = _errs181;
if(vErrors !== null){
if(_errs181){
vErrors.length = _errs181;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data56 = data5.runtime_profile_version_id;
const _errs187 = errors;
let valid38 = false;
const _errs188 = errors;
if(typeof data56 === "string"){
if(!(formats0.test(data56))){
const err160 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err160];
}
else {
vErrors.push(err160);
}
errors++;
}
}
else {
const err161 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err161];
}
else {
vErrors.push(err161);
}
errors++;
}
var _valid14 = _errs188 === errors;
valid38 = valid38 || _valid14;
const _errs190 = errors;
if(data56 !== null){
const err162 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err162];
}
else {
vErrors.push(err162);
}
errors++;
}
var _valid14 = _errs190 === errors;
valid38 = valid38 || _valid14;
if(!valid38){
const err163 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err163];
}
else {
vErrors.push(err163);
}
errors++;
}
else {
errors = _errs187;
if(vErrors !== null){
if(_errs187){
vErrors.length = _errs187;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data57 = data5.budget_usd;
const _errs193 = errors;
const _errs194 = errors;
if(!(((((((data57 === "0") || (data57 === "0.0")) || (data57 === "0.00")) || (data57 === "0.000")) || (data57 === "0.0000")) || (data57 === "0.00000")) || (data57 === "0.000000"))){
const err164 = {};
if(vErrors === null){
vErrors = [err164];
}
else {
vErrors.push(err164);
}
errors++;
}
var valid39 = _errs194 === errors;
if(valid39){
const err165 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err165];
}
else {
vErrors.push(err165);
}
errors++;
}
else {
errors = _errs193;
if(vErrors !== null){
if(_errs193){
vErrors.length = _errs193;
}
else {
vErrors = null;
}
}
}
const _errs195 = errors;
let valid40 = false;
const _errs196 = errors;
if(typeof data57 === "string"){
if(!pattern10.test(data57)){
const err166 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err166];
}
else {
vErrors.push(err166);
}
errors++;
}
}
else {
const err167 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err167];
}
else {
vErrors.push(err167);
}
errors++;
}
var _valid15 = _errs196 === errors;
valid40 = valid40 || _valid15;
const _errs198 = errors;
if(data57 !== null){
const err168 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err168];
}
else {
vErrors.push(err168);
}
errors++;
}
var _valid15 = _errs198 === errors;
valid40 = valid40 || _valid15;
if(!valid40){
const err169 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err169];
}
else {
vErrors.push(err169);
}
errors++;
}
else {
errors = _errs195;
if(vErrors !== null){
if(_errs195){
vErrors.length = _errs195;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data58 = data5.scenario;
if(typeof data58 !== "string"){
const err170 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err170];
}
else {
vErrors.push(err170);
}
errors++;
}
if("exercise" !== data58){
const err171 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "exercise"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err171];
}
else {
vErrors.push(err171);
}
errors++;
}
}
if(data5.organization_name !== undefined){
let data59 = data5.organization_name;
if(typeof data59 === "string"){
if(func1(data59) > 255){
const err172 = {instancePath:instancePath+"/content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err172];
}
else {
vErrors.push(err172);
}
errors++;
}
}
else {
const err173 = {instancePath:instancePath+"/content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err173];
}
else {
vErrors.push(err173);
}
errors++;
}
}
if(data5.known_domains !== undefined){
let data60 = data5.known_domains;
if(Array.isArray(data60)){
if(data60.length > 100){
const err174 = {instancePath:instancePath+"/content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err174];
}
else {
vErrors.push(err174);
}
errors++;
}
const len6 = data60.length;
for(let i6=0; i6<len6; i6++){
let data61 = data60[i6];
if(typeof data61 === "string"){
if(func1(data61) > 253){
const err175 = {instancePath:instancePath+"/content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err175];
}
else {
vErrors.push(err175);
}
errors++;
}
}
else {
const err176 = {instancePath:instancePath+"/content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err176];
}
else {
vErrors.push(err176);
}
errors++;
}
}
}
else {
const err177 = {instancePath:instancePath+"/content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err177];
}
else {
vErrors.push(err177);
}
errors++;
}
}
}
else {
const err178 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err178];
}
else {
vErrors.push(err178);
}
errors++;
}
var _valid1 = _errs162 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 3];
}
else {
if(_valid1){
valid2 = true;
passing0 = 3;
if(props0 !== true){
props0 = true;
}
}
const _errs208 = errors;
const _errs211 = errors;
const _errs212 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
let missing0;
if(((data5.repository_url === undefined) && (missing0 = "repository_url")) || ((data5.source_reference_id === undefined) && (missing0 = "source_reference_id"))){
const err179 = {};
if(vErrors === null){
vErrors = [err179];
}
else {
vErrors.push(err179);
}
errors++;
}
else {
if(data5.repository_url !== undefined){
const _errs213 = errors;
if(typeof data5.repository_url !== "string"){
const err180 = {};
if(vErrors === null){
vErrors = [err180];
}
else {
vErrors.push(err180);
}
errors++;
}
var valid45 = _errs213 === errors;
}
else {
var valid45 = true;
}
if(valid45){
if(data5.source_reference_id !== undefined){
const _errs215 = errors;
if(typeof data5.source_reference_id !== "string"){
const err181 = {};
if(vErrors === null){
vErrors = [err181];
}
else {
vErrors.push(err181);
}
errors++;
}
var valid45 = _errs215 === errors;
}
else {
var valid45 = true;
}
}
}
}
var valid44 = _errs212 === errors;
if(valid44){
const err182 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err182];
}
else {
vErrors.push(err182);
}
errors++;
}
else {
errors = _errs211;
if(vErrors !== null){
if(_errs211){
vErrors.length = _errs211;
}
else {
vErrors = null;
}
}
}
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err183 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err183];
}
else {
vErrors.push(err183);
}
errors++;
}
for(const key5 in data5){
if(!(func22.call(schema86.properties, key5))){
const err184 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key5},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err184];
}
else {
vErrors.push(err184);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data64 = data5.schema_version;
if(typeof data64 !== "string"){
const err185 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err185];
}
else {
vErrors.push(err185);
}
errors++;
}
if("1.0" !== data64){
const err186 = {instancePath:instancePath+"/content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err186];
}
else {
vErrors.push(err186);
}
errors++;
}
}
if(data5.name !== undefined){
let data65 = data5.name;
if(typeof data65 === "string"){
if(func1(data65) > 120){
const err187 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err187];
}
else {
vErrors.push(err187);
}
errors++;
}
}
else {
const err188 = {instancePath:instancePath+"/content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err188];
}
else {
vErrors.push(err188);
}
errors++;
}
}
if(data5.objective !== undefined){
let data66 = data5.objective;
if(typeof data66 === "string"){
if(func1(data66) > 8000){
const err189 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err189];
}
else {
vErrors.push(err189);
}
errors++;
}
}
else {
const err190 = {instancePath:instancePath+"/content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err190];
}
else {
vErrors.push(err190);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data67 = data5.starting_point;
if(typeof data67 === "string"){
if(func1(data67) > 8000){
const err191 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err191];
}
else {
vErrors.push(err191);
}
errors++;
}
}
else {
const err192 = {instancePath:instancePath+"/content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err192];
}
else {
vErrors.push(err192);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data68 = data5.constraints;
if(typeof data68 === "string"){
if(func1(data68) > 4000){
const err193 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err193];
}
else {
vErrors.push(err193);
}
errors++;
}
}
else {
const err194 = {instancePath:instancePath+"/content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err194];
}
else {
vErrors.push(err194);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data69 = data5.reference_ids;
if(Array.isArray(data69)){
if(data69.length > 20){
const err195 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err195];
}
else {
vErrors.push(err195);
}
errors++;
}
const len7 = data69.length;
for(let i7=0; i7<len7; i7++){
let data70 = data69[i7];
if(typeof data70 === "string"){
if(!(formats0.test(data70))){
const err196 = {instancePath:instancePath+"/content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err196];
}
else {
vErrors.push(err196);
}
errors++;
}
}
else {
const err197 = {instancePath:instancePath+"/content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err197];
}
else {
vErrors.push(err197);
}
errors++;
}
}
}
else {
const err198 = {instancePath:instancePath+"/content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err198];
}
else {
vErrors.push(err198);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data71 = data5.model_profile_version_id;
const _errs233 = errors;
let valid49 = false;
const _errs234 = errors;
if(typeof data71 === "string"){
if(!(formats0.test(data71))){
const err199 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err199];
}
else {
vErrors.push(err199);
}
errors++;
}
}
else {
const err200 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err200];
}
else {
vErrors.push(err200);
}
errors++;
}
var _valid16 = _errs234 === errors;
valid49 = valid49 || _valid16;
const _errs236 = errors;
if(data71 !== null){
const err201 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err201];
}
else {
vErrors.push(err201);
}
errors++;
}
var _valid16 = _errs236 === errors;
valid49 = valid49 || _valid16;
if(!valid49){
const err202 = {instancePath:instancePath+"/content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err202];
}
else {
vErrors.push(err202);
}
errors++;
}
else {
errors = _errs233;
if(vErrors !== null){
if(_errs233){
vErrors.length = _errs233;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data72 = data5.runtime_profile_version_id;
const _errs239 = errors;
let valid50 = false;
const _errs240 = errors;
if(typeof data72 === "string"){
if(!(formats0.test(data72))){
const err203 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err203];
}
else {
vErrors.push(err203);
}
errors++;
}
}
else {
const err204 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err204];
}
else {
vErrors.push(err204);
}
errors++;
}
var _valid17 = _errs240 === errors;
valid50 = valid50 || _valid17;
const _errs242 = errors;
if(data72 !== null){
const err205 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err205];
}
else {
vErrors.push(err205);
}
errors++;
}
var _valid17 = _errs242 === errors;
valid50 = valid50 || _valid17;
if(!valid50){
const err206 = {instancePath:instancePath+"/content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err206];
}
else {
vErrors.push(err206);
}
errors++;
}
else {
errors = _errs239;
if(vErrors !== null){
if(_errs239){
vErrors.length = _errs239;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data73 = data5.budget_usd;
const _errs245 = errors;
const _errs246 = errors;
if(!(((((((data73 === "0") || (data73 === "0.0")) || (data73 === "0.00")) || (data73 === "0.000")) || (data73 === "0.0000")) || (data73 === "0.00000")) || (data73 === "0.000000"))){
const err207 = {};
if(vErrors === null){
vErrors = [err207];
}
else {
vErrors.push(err207);
}
errors++;
}
var valid51 = _errs246 === errors;
if(valid51){
const err208 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err208];
}
else {
vErrors.push(err208);
}
errors++;
}
else {
errors = _errs245;
if(vErrors !== null){
if(_errs245){
vErrors.length = _errs245;
}
else {
vErrors = null;
}
}
}
const _errs247 = errors;
let valid52 = false;
const _errs248 = errors;
if(typeof data73 === "string"){
if(!pattern10.test(data73)){
const err209 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err209];
}
else {
vErrors.push(err209);
}
errors++;
}
}
else {
const err210 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err210];
}
else {
vErrors.push(err210);
}
errors++;
}
var _valid18 = _errs248 === errors;
valid52 = valid52 || _valid18;
const _errs250 = errors;
if(data73 !== null){
const err211 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err211];
}
else {
vErrors.push(err211);
}
errors++;
}
var _valid18 = _errs250 === errors;
valid52 = valid52 || _valid18;
if(!valid52){
const err212 = {instancePath:instancePath+"/content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err212];
}
else {
vErrors.push(err212);
}
errors++;
}
else {
errors = _errs247;
if(vErrors !== null){
if(_errs247){
vErrors.length = _errs247;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data74 = data5.scenario;
if(typeof data74 !== "string"){
const err213 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err213];
}
else {
vErrors.push(err213);
}
errors++;
}
if("code_audit" !== data74){
const err214 = {instancePath:instancePath+"/content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "code_audit"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err214];
}
else {
vErrors.push(err214);
}
errors++;
}
}
if(data5.repository_url !== undefined){
let data75 = data5.repository_url;
const _errs255 = errors;
let valid53 = false;
const _errs256 = errors;
if(typeof data75 === "string"){
if(func1(data75) > 2048){
const err215 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err215];
}
else {
vErrors.push(err215);
}
errors++;
}
}
else {
const err216 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err216];
}
else {
vErrors.push(err216);
}
errors++;
}
var _valid19 = _errs256 === errors;
valid53 = valid53 || _valid19;
const _errs258 = errors;
if(data75 !== null){
const err217 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err217];
}
else {
vErrors.push(err217);
}
errors++;
}
var _valid19 = _errs258 === errors;
valid53 = valid53 || _valid19;
if(!valid53){
const err218 = {instancePath:instancePath+"/content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err218];
}
else {
vErrors.push(err218);
}
errors++;
}
else {
errors = _errs255;
if(vErrors !== null){
if(_errs255){
vErrors.length = _errs255;
}
else {
vErrors = null;
}
}
}
}
if(data5.source_reference_id !== undefined){
let data76 = data5.source_reference_id;
const _errs261 = errors;
let valid54 = false;
const _errs262 = errors;
if(typeof data76 === "string"){
if(!(formats0.test(data76))){
const err219 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err219];
}
else {
vErrors.push(err219);
}
errors++;
}
}
else {
const err220 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err220];
}
else {
vErrors.push(err220);
}
errors++;
}
var _valid20 = _errs262 === errors;
valid54 = valid54 || _valid20;
const _errs264 = errors;
if(data76 !== null){
const err221 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err221];
}
else {
vErrors.push(err221);
}
errors++;
}
var _valid20 = _errs264 === errors;
valid54 = valid54 || _valid20;
if(!valid54){
const err222 = {instancePath:instancePath+"/content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err222];
}
else {
vErrors.push(err222);
}
errors++;
}
else {
errors = _errs261;
if(vErrors !== null){
if(_errs261){
vErrors.length = _errs261;
}
else {
vErrors = null;
}
}
}
}
if(data5.revision !== undefined){
let data77 = data5.revision;
const _errs267 = errors;
let valid55 = false;
const _errs268 = errors;
if(typeof data77 === "string"){
if(func1(data77) > 255){
const err223 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err223];
}
else {
vErrors.push(err223);
}
errors++;
}
}
else {
const err224 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err224];
}
else {
vErrors.push(err224);
}
errors++;
}
var _valid21 = _errs268 === errors;
valid55 = valid55 || _valid21;
const _errs270 = errors;
if(data77 !== null){
const err225 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err225];
}
else {
vErrors.push(err225);
}
errors++;
}
var _valid21 = _errs270 === errors;
valid55 = valid55 || _valid21;
if(!valid55){
const err226 = {instancePath:instancePath+"/content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err226];
}
else {
vErrors.push(err226);
}
errors++;
}
else {
errors = _errs267;
if(vErrors !== null){
if(_errs267){
vErrors.length = _errs267;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err227 = {instancePath:instancePath+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err227];
}
else {
vErrors.push(err227);
}
errors++;
}
var _valid1 = _errs208 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 4];
}
else {
if(_valid1){
valid2 = true;
passing0 = 4;
if(props0 !== true){
props0 = true;
}
}
}
}
}
}
if(!valid2){
const err228 = {instancePath:instancePath+"/content",schemaPath:"#/properties/content/anyOf/0/oneOf",keyword:"oneOf",params:{passingSchemas: passing0},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err228];
}
else {
vErrors.push(err228);
}
errors++;
}
else {
errors = _errs15;
if(vErrors !== null){
if(_errs15){
vErrors.length = _errs15;
}
else {
vErrors = null;
}
}
}
var _valid0 = _errs14 === errors;
valid1 = valid1 || _valid0;
const _errs272 = errors;
const _errs273 = errors;
let valid56 = false;
let passing1 = null;
const _errs274 = errors;
if(!(validate40(data5, {instancePath:instancePath+"/content",parentData:data,parentDataProperty:"content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate40.errors : vErrors.concat(validate40.errors);
errors = vErrors.length;
}
var _valid22 = _errs274 === errors;
if(_valid22){
valid56 = true;
passing1 = 0;
var props1 = true;
}
const _errs275 = errors;
if(!(validate42(data5, {instancePath:instancePath+"/content",parentData:data,parentDataProperty:"content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate42.errors : vErrors.concat(validate42.errors);
errors = vErrors.length;
}
var _valid22 = _errs275 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 1];
}
else {
if(_valid22){
valid56 = true;
passing1 = 1;
if(props1 !== true){
props1 = true;
}
}
const _errs276 = errors;
if(!(validate50(data5, {instancePath:instancePath+"/content",parentData:data,parentDataProperty:"content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate50.errors : vErrors.concat(validate50.errors);
errors = vErrors.length;
}
var _valid22 = _errs276 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 2];
}
else {
if(_valid22){
valid56 = true;
passing1 = 2;
if(props1 !== true){
props1 = true;
}
}
const _errs277 = errors;
if(!(validate52(data5, {instancePath:instancePath+"/content",parentData:data,parentDataProperty:"content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate52.errors : vErrors.concat(validate52.errors);
errors = vErrors.length;
}
var _valid22 = _errs277 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 3];
}
else {
if(_valid22){
valid56 = true;
passing1 = 3;
if(props1 !== true){
props1 = true;
}
}
const _errs278 = errors;
if(!(validate54(data5, {instancePath:instancePath+"/content",parentData:data,parentDataProperty:"content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate54.errors : vErrors.concat(validate54.errors);
errors = vErrors.length;
}
var _valid22 = _errs278 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 4];
}
else {
if(_valid22){
valid56 = true;
passing1 = 4;
if(props1 !== true){
props1 = true;
}
}
}
}
}
}
if(!valid56){
const err229 = {instancePath:instancePath+"/content",schemaPath:"#/properties/content/anyOf/1/oneOf",keyword:"oneOf",params:{passingSchemas: passing1},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err229];
}
else {
vErrors.push(err229);
}
errors++;
}
else {
errors = _errs273;
if(vErrors !== null){
if(_errs273){
vErrors.length = _errs273;
}
else {
vErrors = null;
}
}
}
var _valid0 = _errs272 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
if(props0 !== true && props1 !== undefined){
if(props1 === true){
props0 = true;
}
else {
props0 = props0 || {};
Object.assign(props0, props1);
}
}
}
if(!valid1){
const err230 = {instancePath:instancePath+"/content",schemaPath:"#/properties/content/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err230];
}
else {
vErrors.push(err230);
}
errors++;
}
else {
errors = _errs13;
if(vErrors !== null){
if(_errs13){
vErrors.length = _errs13;
}
else {
vErrors = null;
}
}
}
}
if(data.selected_model_summary !== undefined){
let data78 = data.selected_model_summary;
const _errs280 = errors;
let valid57 = false;
const _errs281 = errors;
if(data78 && typeof data78 == "object" && !Array.isArray(data78)){
}
else {
const err231 = {instancePath:instancePath+"/selected_model_summary",schemaPath:"#/properties/selected_model_summary/anyOf/0/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err231];
}
else {
vErrors.push(err231);
}
errors++;
}
var _valid23 = _errs281 === errors;
valid57 = valid57 || _valid23;
const _errs284 = errors;
if(data78 !== null){
const err232 = {instancePath:instancePath+"/selected_model_summary",schemaPath:"#/properties/selected_model_summary/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err232];
}
else {
vErrors.push(err232);
}
errors++;
}
var _valid23 = _errs284 === errors;
valid57 = valid57 || _valid23;
if(!valid57){
const err233 = {instancePath:instancePath+"/selected_model_summary",schemaPath:"#/properties/selected_model_summary/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err233];
}
else {
vErrors.push(err233);
}
errors++;
}
else {
errors = _errs280;
if(vErrors !== null){
if(_errs280){
vErrors.length = _errs280;
}
else {
vErrors = null;
}
}
}
}
if(data.last_created_task_id !== undefined){
let data79 = data.last_created_task_id;
const _errs287 = errors;
let valid58 = false;
const _errs288 = errors;
if(typeof data79 === "string"){
if(!(formats0.test(data79))){
const err234 = {instancePath:instancePath+"/last_created_task_id",schemaPath:"#/properties/last_created_task_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err234];
}
else {
vErrors.push(err234);
}
errors++;
}
}
else {
const err235 = {instancePath:instancePath+"/last_created_task_id",schemaPath:"#/properties/last_created_task_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err235];
}
else {
vErrors.push(err235);
}
errors++;
}
var _valid24 = _errs288 === errors;
valid58 = valid58 || _valid24;
const _errs290 = errors;
if(data79 !== null){
const err236 = {instancePath:instancePath+"/last_created_task_id",schemaPath:"#/properties/last_created_task_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err236];
}
else {
vErrors.push(err236);
}
errors++;
}
var _valid24 = _errs290 === errors;
valid58 = valid58 || _valid24;
if(!valid58){
const err237 = {instancePath:instancePath+"/last_created_task_id",schemaPath:"#/properties/last_created_task_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err237];
}
else {
vErrors.push(err237);
}
errors++;
}
else {
errors = _errs287;
if(vErrors !== null){
if(_errs287){
vErrors.length = _errs287;
}
else {
vErrors = null;
}
}
}
}
if(data.created_at !== undefined){
let data80 = data.created_at;
if(typeof data80 === "string"){
if(!(formats2.validate(data80))){
const err238 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err238];
}
else {
vErrors.push(err238);
}
errors++;
}
}
else {
const err239 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err239];
}
else {
vErrors.push(err239);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data81 = data.updated_at;
if(typeof data81 === "string"){
if(!(formats2.validate(data81))){
const err240 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err240];
}
else {
vErrors.push(err240);
}
errors++;
}
}
else {
const err241 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err241];
}
else {
vErrors.push(err241);
}
errors++;
}
}
}
else {
const err242 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err242];
}
else {
vErrors.push(err242);
}
errors++;
}
validate73.errors = vErrors;
return errors === 0;
}
validate73.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateSavedTaskDraftPage = validate79;
const schema87 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/SavedTaskDraft"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"maxLength":512,"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"TaskDraftPageResponse","type":"object"};

function validate79(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate79.evaluated;
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
if(!(validate73(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate73.errors : vErrors.concat(validate73.errors);
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
const _errs6 = errors;
let valid3 = false;
const _errs7 = errors;
if(typeof data2 === "string"){
if(func1(data2) > 512){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 512},message:"must NOT have more than 512 characters"};
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
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
var _valid0 = _errs7 === errors;
valid3 = valid3 || _valid0;
const _errs9 = errors;
if(data2 !== null){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
var _valid0 = _errs9 === errors;
valid3 = valid3 || _valid0;
if(!valid3){
const err8 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
else {
errors = _errs6;
if(vErrors !== null){
if(_errs6){
vErrors.length = _errs6;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err9 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
validate79.errors = vErrors;
return errors === 0;
}
validate79.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTenantPage = validate81;
const schema88 = {"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Tenant"},"type":"array","maxItems":100,"title":"Items"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"additionalProperties":false,"type":"object","required":["items","next_cursor"],"title":"TenantPage"};
const schema89 = {"properties":{"id":{"type":"string","format":"uuid","title":"Id"},"name":{"type":"string","title":"Name"},"permissions":{"items":{"type":"string","enum":["model.config.read","model.config.write"]},"type":"array","title":"Permissions"}},"additionalProperties":false,"type":"object","required":["id","name","permissions"],"title":"TenantResponse"};

function validate81(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate81.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.name === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.permissions === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/required",keyword:"required",params:{missingProperty: "permissions"},message:"must have required property '"+"permissions"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
for(const key1 in data1){
if(!(((key1 === "id") || (key1 === "name")) || (key1 === "permissions"))){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err8 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err9 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data1.name !== undefined){
if(typeof data1.name !== "string"){
const err10 = {instancePath:instancePath+"/items/" + i0+"/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data1.permissions !== undefined){
let data4 = data1.permissions;
if(Array.isArray(data4)){
const len1 = data4.length;
for(let i1=0; i1<len1; i1++){
let data5 = data4[i1];
if(typeof data5 !== "string"){
const err11 = {instancePath:instancePath+"/items/" + i0+"/permissions/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/permissions/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(!((data5 === "model.config.read") || (data5 === "model.config.write"))){
const err12 = {instancePath:instancePath+"/items/" + i0+"/permissions/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/permissions/items/enum",keyword:"enum",params:{allowedValues: schema89.properties.permissions.items.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
}
else {
const err13 = {instancePath:instancePath+"/items/" + i0+"/permissions",schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/properties/permissions/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
}
else {
const err14 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Tenant/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
const err15 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data6 = data.next_cursor;
const _errs17 = errors;
let valid7 = false;
const _errs18 = errors;
if(typeof data6 !== "string"){
const err16 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
var _valid0 = _errs18 === errors;
valid7 = valid7 || _valid0;
const _errs20 = errors;
if(data6 !== null){
const err17 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid7 = valid7 || _valid0;
if(!valid7){
const err18 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
else {
errors = _errs17;
if(vErrors !== null){
if(_errs17){
vErrors.length = _errs17;
}
else {
vErrors = null;
}
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
validate81.errors = vErrors;
return errors === 0;
}
validate81.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateModelDefinitionPage = validate82;
const schema90 = {"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ModelDefinition"},"type":"array","maxItems":100,"title":"Items"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"additionalProperties":false,"type":"object","required":["items","next_cursor"],"title":"ModelDefinitionPage"};
const schema91 = {"properties":{"id":{"type":"string","format":"uuid","title":"Id"},"tenant_id":{"type":"string","format":"uuid","title":"Tenant Id"},"kind":{"type":"string","enum":["service","profile"],"title":"Kind"},"name":{"type":"string","title":"Name"},"created_at":{"type":"string","format":"date-time","title":"Created At"}},"additionalProperties":false,"type":"object","required":["id","tenant_id","kind","name","created_at"],"title":"ModelDefinitionResponse"};

function validate82(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate82.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.tenant_id === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/required",keyword:"required",params:{missingProperty: "tenant_id"},message:"must have required property '"+"tenant_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.kind === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.name === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.created_at === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
for(const key1 in data1){
if(!(((((key1 === "id") || (key1 === "tenant_id")) || (key1 === "kind")) || (key1 === "name")) || (key1 === "created_at"))){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err10 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err11 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data1.tenant_id !== undefined){
let data3 = data1.tenant_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err12 = {instancePath:instancePath+"/items/" + i0+"/tenant_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err13 = {instancePath:instancePath+"/items/" + i0+"/tenant_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data1.kind !== undefined){
let data4 = data1.kind;
if(typeof data4 !== "string"){
const err14 = {instancePath:instancePath+"/items/" + i0+"/kind",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(!((data4 === "service") || (data4 === "profile"))){
const err15 = {instancePath:instancePath+"/items/" + i0+"/kind",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/kind/enum",keyword:"enum",params:{allowedValues: schema91.properties.kind.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data1.name !== undefined){
if(typeof data1.name !== "string"){
const err16 = {instancePath:instancePath+"/items/" + i0+"/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data1.created_at !== undefined){
let data6 = data1.created_at;
if(typeof data6 === "string"){
if(!(formats2.validate(data6))){
const err17 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
else {
const err18 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err19 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelDefinition/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
else {
const err20 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data7 = data.next_cursor;
const _errs19 = errors;
let valid5 = false;
const _errs20 = errors;
if(typeof data7 !== "string"){
const err21 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid5 = valid5 || _valid0;
const _errs22 = errors;
if(data7 !== null){
const err22 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
var _valid0 = _errs22 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err23 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
else {
errors = _errs19;
if(vErrors !== null){
if(_errs19){
vErrors.length = _errs19;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err24 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
validate82.errors = vErrors;
return errors === 0;
}
validate82.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateModelVersion = validate83;
const schema92 = {"properties":{"id":{"type":"string","format":"uuid","title":"Id"},"tenant_id":{"type":"string","format":"uuid","title":"Tenant Id"},"definition_id":{"type":"string","format":"uuid","title":"Definition Id"},"kind":{"type":"string","enum":["service","profile"],"title":"Kind"},"number":{"type":"integer","maximum":9007199254740991,"minimum":1,"title":"Number"},"name":{"type":"string","title":"Name"},"config":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/ServiceConfig"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ProfileConfig"}],"title":"Config"},"state":{"type":"string","enum":["draft","published","retired","revoked"],"title":"State"},"state_revision":{"type":"integer","maximum":9007199254740991,"minimum":1,"title":"State Revision"},"sync_state":{"type":"string","enum":["pending","synced","failed","unknown"],"title":"Sync State"},"created_at":{"type":"string","format":"date-time","title":"Created At"}},"additionalProperties":false,"type":"object","required":["id","tenant_id","definition_id","kind","number","name","config","state","state_revision","sync_state","created_at"],"title":"ModelVersionResponse"};
const schema93 = {"properties":{"protocol":{"type":"string","enum":["openai","anthropic"],"title":"Protocol"},"base_url":{"type":"string","maxLength":2048,"minLength":1,"title":"Base Url"}},"additionalProperties":false,"type":"object","required":["protocol","base_url"],"title":"ServiceConfig"};

function validate83(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate83.evaluated;
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
if(data.definition_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "definition_id"},message:"must have required property '"+"definition_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.kind === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.number === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "number"},message:"must have required property '"+"number"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.name === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.config === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "config"},message:"must have required property '"+"config"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.state === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.state_revision === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state_revision"},message:"must have required property '"+"state_revision"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.sync_state === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "sync_state"},message:"must have required property '"+"sync_state"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.created_at === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema92.properties, key0))){
const err11 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err12 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err13 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.tenant_id !== undefined){
let data1 = data.tenant_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err14 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/tenant_id",schemaPath:"#/properties/tenant_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.definition_id !== undefined){
let data2 = data.definition_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err16 = {instancePath:instancePath+"/definition_id",schemaPath:"#/properties/definition_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err17 = {instancePath:instancePath+"/definition_id",schemaPath:"#/properties/definition_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.kind !== undefined){
let data3 = data.kind;
if(typeof data3 !== "string"){
const err18 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(!((data3 === "service") || (data3 === "profile"))){
const err19 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/enum",keyword:"enum",params:{allowedValues: schema92.properties.kind.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.number !== undefined){
let data4 = data.number;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err20 = {instancePath:instancePath+"/number",schemaPath:"#/properties/number/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if((typeof data4 == "number") && (isFinite(data4))){
if(data4 > 9007199254740991 || isNaN(data4)){
const err21 = {instancePath:instancePath+"/number",schemaPath:"#/properties/number/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data4 < 1 || isNaN(data4)){
const err22 = {instancePath:instancePath+"/number",schemaPath:"#/properties/number/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
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
if(data.name !== undefined){
if(typeof data.name !== "string"){
const err23 = {instancePath:instancePath+"/name",schemaPath:"#/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.config !== undefined){
let data6 = data.config;
const _errs15 = errors;
let valid1 = false;
const _errs16 = errors;
if(data6 && typeof data6 == "object" && !Array.isArray(data6)){
if(data6.protocol === undefined){
const err24 = {instancePath:instancePath+"/config",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/required",keyword:"required",params:{missingProperty: "protocol"},message:"must have required property '"+"protocol"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if(data6.base_url === undefined){
const err25 = {instancePath:instancePath+"/config",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/required",keyword:"required",params:{missingProperty: "base_url"},message:"must have required property '"+"base_url"+"'"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
for(const key1 in data6){
if(!((key1 === "protocol") || (key1 === "base_url"))){
const err26 = {instancePath:instancePath+"/config",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data6.protocol !== undefined){
let data7 = data6.protocol;
if(typeof data7 !== "string"){
const err27 = {instancePath:instancePath+"/config/protocol",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/properties/protocol/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
if(!((data7 === "openai") || (data7 === "anthropic"))){
const err28 = {instancePath:instancePath+"/config/protocol",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/properties/protocol/enum",keyword:"enum",params:{allowedValues: schema93.properties.protocol.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data6.base_url !== undefined){
let data8 = data6.base_url;
if(typeof data8 === "string"){
if(func1(data8) > 2048){
const err29 = {instancePath:instancePath+"/config/base_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/properties/base_url/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
if(func1(data8) < 1){
const err30 = {instancePath:instancePath+"/config/base_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/properties/base_url/minLength",keyword:"minLength",params:{limit: 1},message:"must NOT have fewer than 1 characters"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/config/base_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/properties/base_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err32 = {instancePath:instancePath+"/config",schemaPath:"urn:wuji:contracts:0.5#/$defs/ServiceConfig/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
var _valid0 = _errs16 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
var props0 = true;
}
const _errs24 = errors;
if(!(validate58(data6, {instancePath:instancePath+"/config",parentData:data,parentDataProperty:"config",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate58.errors : vErrors.concat(validate58.errors);
errors = vErrors.length;
}
var _valid0 = _errs24 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
if(props0 !== true){
props0 = true;
}
}
if(!valid1){
const err33 = {instancePath:instancePath+"/config",schemaPath:"#/properties/config/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
else {
errors = _errs15;
if(vErrors !== null){
if(_errs15){
vErrors.length = _errs15;
}
else {
vErrors = null;
}
}
}
}
if(data.state !== undefined){
let data9 = data.state;
if(typeof data9 !== "string"){
const err34 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(!((((data9 === "draft") || (data9 === "published")) || (data9 === "retired")) || (data9 === "revoked"))){
const err35 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema92.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
if(data.state_revision !== undefined){
let data10 = data.state_revision;
if(!(((typeof data10 == "number") && (!(data10 % 1) && !isNaN(data10))) && (isFinite(data10)))){
const err36 = {instancePath:instancePath+"/state_revision",schemaPath:"#/properties/state_revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
if((typeof data10 == "number") && (isFinite(data10))){
if(data10 > 9007199254740991 || isNaN(data10)){
const err37 = {instancePath:instancePath+"/state_revision",schemaPath:"#/properties/state_revision/maximum",keyword:"maximum",params:{comparison: "<=", limit: 9007199254740991},message:"must be <= 9007199254740991"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(data10 < 1 || isNaN(data10)){
const err38 = {instancePath:instancePath+"/state_revision",schemaPath:"#/properties/state_revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
}
if(data.sync_state !== undefined){
let data11 = data.sync_state;
if(typeof data11 !== "string"){
const err39 = {instancePath:instancePath+"/sync_state",schemaPath:"#/properties/sync_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
if(!((((data11 === "pending") || (data11 === "synced")) || (data11 === "failed")) || (data11 === "unknown"))){
const err40 = {instancePath:instancePath+"/sync_state",schemaPath:"#/properties/sync_state/enum",keyword:"enum",params:{allowedValues: schema92.properties.sync_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
if(data.created_at !== undefined){
let data12 = data.created_at;
if(typeof data12 === "string"){
if(!(formats2.validate(data12))){
const err41 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err43 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
validate83.errors = vErrors;
return errors === 0;
}
validate83.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateModelVersionPage = validate85;
const schema94 = {"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ModelVersion"},"type":"array","maxItems":100,"title":"Items"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"additionalProperties":false,"type":"object","required":["items","next_cursor"],"title":"ModelVersionPage"};

function validate85(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate85.evaluated;
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
if(!(validate83(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate83.errors : vErrors.concat(validate83.errors);
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
const _errs6 = errors;
let valid3 = false;
const _errs7 = errors;
if(typeof data2 !== "string"){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
var _valid0 = _errs7 === errors;
valid3 = valid3 || _valid0;
const _errs9 = errors;
if(data2 !== null){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
var _valid0 = _errs9 === errors;
valid3 = valid3 || _valid0;
if(!valid3){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
else {
errors = _errs6;
if(vErrors !== null){
if(_errs6){
vErrors.length = _errs6;
}
else {
vErrors = null;
}
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
validate85.errors = vErrors;
return errors === 0;
}
validate85.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateModelOperation = validate87;
const schema95 = {"properties":{"id":{"type":"string","format":"uuid","title":"Id"},"kind":{"type":"string","enum":["create_service","create_profile","check","publish","retire","revoke"],"title":"Kind"},"version_id":{"type":"string","format":"uuid","title":"Version Id"},"state":{"type":"string","enum":["prepared","sent","succeeded","failed","unknown"],"title":"State"},"result":{"$ref":"urn:wuji:contracts:0.5#/$defs/ModelOperationResult"},"created_at":{"type":"string","format":"date-time","title":"Created At"},"updated_at":{"type":"string","format":"date-time","title":"Updated At"}},"additionalProperties":false,"type":"object","required":["id","kind","version_id","state","result","created_at","updated_at"],"title":"ModelOperationResponse"};
const schema96 = {"properties":{"error_code":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Error Code"},"usage":{"type":"null","title":"Usage"},"cost_usd":{"type":"null","title":"Cost Usd"}},"additionalProperties":false,"type":"object","title":"ModelOperationResult"};

function validate87(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate87.evaluated;
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
if(data.kind === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.version_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "version_id"},message:"must have required property '"+"version_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.state === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.result === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "result"},message:"must have required property '"+"result"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.created_at === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.updated_at === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
for(const key0 in data){
if(!(((((((key0 === "id") || (key0 === "kind")) || (key0 === "version_id")) || (key0 === "state")) || (key0 === "result")) || (key0 === "created_at")) || (key0 === "updated_at"))){
const err7 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err8 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err9 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.kind !== undefined){
let data1 = data.kind;
if(typeof data1 !== "string"){
const err10 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(!((((((data1 === "create_service") || (data1 === "create_profile")) || (data1 === "check")) || (data1 === "publish")) || (data1 === "retire")) || (data1 === "revoke"))){
const err11 = {instancePath:instancePath+"/kind",schemaPath:"#/properties/kind/enum",keyword:"enum",params:{allowedValues: schema95.properties.kind.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.version_id !== undefined){
let data2 = data.version_id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err12 = {instancePath:instancePath+"/version_id",schemaPath:"#/properties/version_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err13 = {instancePath:instancePath+"/version_id",schemaPath:"#/properties/version_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data.state !== undefined){
let data3 = data.state;
if(typeof data3 !== "string"){
const err14 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(!(((((data3 === "prepared") || (data3 === "sent")) || (data3 === "succeeded")) || (data3 === "failed")) || (data3 === "unknown"))){
const err15 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema95.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.result !== undefined){
let data4 = data.result;
if(data4 && typeof data4 == "object" && !Array.isArray(data4)){
for(const key1 in data4){
if(!(((key1 === "error_code") || (key1 === "usage")) || (key1 === "cost_usd"))){
const err16 = {instancePath:instancePath+"/result",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data4.error_code !== undefined){
let data5 = data4.error_code;
const _errs15 = errors;
let valid3 = false;
const _errs16 = errors;
if(typeof data5 !== "string"){
const err17 = {instancePath:instancePath+"/result/error_code",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/properties/error_code/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid0 = _errs16 === errors;
valid3 = valid3 || _valid0;
const _errs18 = errors;
if(data5 !== null){
const err18 = {instancePath:instancePath+"/result/error_code",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/properties/error_code/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
var _valid0 = _errs18 === errors;
valid3 = valid3 || _valid0;
if(!valid3){
const err19 = {instancePath:instancePath+"/result/error_code",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/properties/error_code/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
else {
errors = _errs15;
if(vErrors !== null){
if(_errs15){
vErrors.length = _errs15;
}
else {
vErrors = null;
}
}
}
}
if(data4.usage !== undefined){
if(data4.usage !== null){
const err20 = {instancePath:instancePath+"/result/usage",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/properties/usage/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data4.cost_usd !== undefined){
if(data4.cost_usd !== null){
const err21 = {instancePath:instancePath+"/result/cost_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/properties/cost_usd/type",keyword:"type",params:{type: "null"},message:"must be null"};
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
const err22 = {instancePath:instancePath+"/result",schemaPath:"urn:wuji:contracts:0.5#/$defs/ModelOperationResult/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data.created_at !== undefined){
let data8 = data.created_at;
if(typeof data8 === "string"){
if(!(formats2.validate(data8))){
const err23 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
else {
const err24 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data.updated_at !== undefined){
let data9 = data.updated_at;
if(typeof data9 === "string"){
if(!(formats2.validate(data9))){
const err25 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
else {
const err26 = {instancePath:instancePath+"/updated_at",schemaPath:"#/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
}
else {
const err27 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
validate87.errors = vErrors;
return errors === 0;
}
validate87.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateScenarioProfilePage = validate88;
const schema97 = {"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ScenarioProfile"},"maxItems":5,"minItems":5,"title":"Items","type":"array"}},"required":["items"],"title":"ScenarioProfilePage","type":"object"};
const schema98 = {"additionalProperties":false,"properties":{"schema_version":{"const":"1.0","title":"Schema Version","type":"string"},"id":{"title":"Id","type":"string"},"version":{"title":"Version","type":"integer"},"scenario":{"enum":["ctf","web_single","comprehensive","exercise","code_audit"],"title":"Scenario","type":"string"},"name":{"title":"Name","type":"string"},"objective":{"title":"Objective","type":"string"},"completion_criteria":{"items":{"type":"string"},"title":"Completion Criteria","type":"array"},"digest":{"title":"Digest","type":"string"},"can_create":{"title":"Can Create","type":"boolean"}},"required":["schema_version","id","version","scenario","name","objective","completion_criteria","digest","can_create"],"title":"ScenarioProfile","type":"object"};

function validate88(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate88.evaluated;
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
if(data.items !== undefined){
let data0 = data.items;
if(Array.isArray(data0)){
if(data0.length > 5){
const err1 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 5},message:"must NOT have more than 5 items"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data0.length < 5){
const err2 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/minItems",keyword:"minItems",params:{limit: 5},message:"must NOT have fewer than 5 items"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
const len0 = data0.length;
for(let i0=0; i0<len0; i0++){
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.schema_version === undefined){
const err3 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "schema_version"},message:"must have required property '"+"schema_version"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.version === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "version"},message:"must have required property '"+"version"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.scenario === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.name === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.objective === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "objective"},message:"must have required property '"+"objective"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data1.completion_criteria === undefined){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "completion_criteria"},message:"must have required property '"+"completion_criteria"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data1.digest === undefined){
const err10 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data1.can_create === undefined){
const err11 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/required",keyword:"required",params:{missingProperty: "can_create"},message:"must have required property '"+"can_create"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key0 in data1){
if(!(func22.call(schema98.properties, key0))){
const err12 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data1.schema_version !== undefined){
let data2 = data1.schema_version;
if(typeof data2 !== "string"){
const err13 = {instancePath:instancePath+"/items/" + i0+"/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if("1.0" !== data2){
const err14 = {instancePath:instancePath+"/items/" + i0+"/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data1.id !== undefined){
if(typeof data1.id !== "string"){
const err15 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data1.version !== undefined){
let data4 = data1.version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err16 = {instancePath:instancePath+"/items/" + i0+"/version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data1.scenario !== undefined){
let data5 = data1.scenario;
if(typeof data5 !== "string"){
const err17 = {instancePath:instancePath+"/items/" + i0+"/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(!(((((data5 === "ctf") || (data5 === "web_single")) || (data5 === "comprehensive")) || (data5 === "exercise")) || (data5 === "code_audit"))){
const err18 = {instancePath:instancePath+"/items/" + i0+"/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/scenario/enum",keyword:"enum",params:{allowedValues: schema98.properties.scenario.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data1.name !== undefined){
if(typeof data1.name !== "string"){
const err19 = {instancePath:instancePath+"/items/" + i0+"/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data1.objective !== undefined){
if(typeof data1.objective !== "string"){
const err20 = {instancePath:instancePath+"/items/" + i0+"/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data1.completion_criteria !== undefined){
let data8 = data1.completion_criteria;
if(Array.isArray(data8)){
const len1 = data8.length;
for(let i1=0; i1<len1; i1++){
if(typeof data8[i1] !== "string"){
const err21 = {instancePath:instancePath+"/items/" + i0+"/completion_criteria/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/completion_criteria/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err22 = {instancePath:instancePath+"/items/" + i0+"/completion_criteria",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/completion_criteria/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data1.digest !== undefined){
if(typeof data1.digest !== "string"){
const err23 = {instancePath:instancePath+"/items/" + i0+"/digest",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data1.can_create !== undefined){
if(typeof data1.can_create !== "boolean"){
const err24 = {instancePath:instancePath+"/items/" + i0+"/can_create",schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/properties/can_create/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
}
else {
const err25 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ScenarioProfile/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
}
else {
const err26 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
}
else {
const err27 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
validate88.errors = vErrors;
return errors === 0;
}
validate88.evaluated = {"props":{"items":true},"dynamicProps":false,"dynamicItems":false};

export const validateTaskCreationPreview = validate89;
const schema99 = {"additionalProperties":false,"properties":{"preview_id":{"format":"uuid","title":"Preview Id","type":"string"},"project_id":{"format":"uuid","title":"Project Id","type":"string"},"start_available":{"const":false,"default":false,"title":"Start Available","type":"boolean"},"draft_id":{"format":"uuid","title":"Draft Id","type":"string"},"draft_version":{"title":"Draft Version","type":"integer"},"normalized_content":{"anyOf":[{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraft"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft"}]},{"oneOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/CtfDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/WebDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/ExerciseDraftV2"},{"$ref":"urn:wuji:contracts:0.5#/$defs/CodeAuditDraftV2"}]}],"title":"Normalized Content"},"model_snapshot":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/SelectedModelSnapshot"},{"type":"null"}]},"input_digest":{"title":"Input Digest","type":"string"},"authorization_digest":{"title":"Authorization Digest","type":"string"},"can_create":{"title":"Can Create","type":"boolean"},"blockers":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/CreationBlocker"},"title":"Blockers","type":"array"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"expires_at":{"format":"date-time","title":"Expires At","type":"string"}},"required":["preview_id","project_id","draft_id","draft_version","normalized_content","model_snapshot","input_digest","authorization_digest","can_create","blockers","created_at","expires_at"],"title":"TaskCreationPreview","type":"object"};
const schema105 = {"properties":{"code":{"title":"Code","type":"string"},"message":{"title":"Message","type":"string"}},"required":["code","message"],"title":"CreationBlocker","type":"object"};

function validate89(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate89.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.preview_id === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "preview_id"},message:"must have required property '"+"preview_id"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.project_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project_id"},message:"must have required property '"+"project_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.draft_id === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "draft_id"},message:"must have required property '"+"draft_id"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.draft_version === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "draft_version"},message:"must have required property '"+"draft_version"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.normalized_content === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "normalized_content"},message:"must have required property '"+"normalized_content"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.model_snapshot === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "model_snapshot"},message:"must have required property '"+"model_snapshot"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.input_digest === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "input_digest"},message:"must have required property '"+"input_digest"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.authorization_digest === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "authorization_digest"},message:"must have required property '"+"authorization_digest"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data.can_create === undefined){
const err8 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "can_create"},message:"must have required property '"+"can_create"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data.blockers === undefined){
const err9 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "blockers"},message:"must have required property '"+"blockers"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data.created_at === undefined){
const err10 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data.expires_at === undefined){
const err11 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "expires_at"},message:"must have required property '"+"expires_at"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema99.properties, key0))){
const err12 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.preview_id !== undefined){
let data0 = data.preview_id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err13 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
else {
const err14 = {instancePath:instancePath+"/preview_id",schemaPath:"#/properties/preview_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data.project_id !== undefined){
let data1 = data.project_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err15 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
else {
const err16 = {instancePath:instancePath+"/project_id",schemaPath:"#/properties/project_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.start_available !== undefined){
let data2 = data.start_available;
if(typeof data2 !== "boolean"){
const err17 = {instancePath:instancePath+"/start_available",schemaPath:"#/properties/start_available/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(false !== data2){
const err18 = {instancePath:instancePath+"/start_available",schemaPath:"#/properties/start_available/const",keyword:"const",params:{allowedValue: false},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.draft_id !== undefined){
let data3 = data.draft_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err19 = {instancePath:instancePath+"/draft_id",schemaPath:"#/properties/draft_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err20 = {instancePath:instancePath+"/draft_id",schemaPath:"#/properties/draft_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data.draft_version !== undefined){
let data4 = data.draft_version;
if(!(((typeof data4 == "number") && (!(data4 % 1) && !isNaN(data4))) && (isFinite(data4)))){
const err21 = {instancePath:instancePath+"/draft_version",schemaPath:"#/properties/draft_version/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.normalized_content !== undefined){
let data5 = data.normalized_content;
const _errs13 = errors;
let valid1 = false;
const _errs14 = errors;
const _errs15 = errors;
let valid2 = false;
let passing0 = null;
const _errs16 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err22 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
for(const key1 in data5){
if(!(func22.call(schema82.properties, key1))){
const err23 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data6 = data5.schema_version;
if(typeof data6 !== "string"){
const err24 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if("1.0" !== data6){
const err25 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data5.name !== undefined){
let data7 = data5.name;
if(typeof data7 === "string"){
if(func1(data7) > 120){
const err26 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
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
const err27 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data5.objective !== undefined){
let data8 = data5.objective;
if(typeof data8 === "string"){
if(func1(data8) > 8000){
const err28 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data9 = data5.starting_point;
if(typeof data9 === "string"){
if(func1(data9) > 8000){
const err30 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
else {
const err31 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data10 = data5.constraints;
if(typeof data10 === "string"){
if(func1(data10) > 4000){
const err32 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
else {
const err33 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data11 = data5.reference_ids;
if(Array.isArray(data11)){
if(data11.length > 20){
const err34 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
const len0 = data11.length;
for(let i0=0; i0<len0; i0++){
let data12 = data11[i0];
if(typeof data12 === "string"){
if(!(formats0.test(data12))){
const err35 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
else {
const err36 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
const err37 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data13 = data5.model_profile_version_id;
const _errs35 = errors;
let valid7 = false;
const _errs36 = errors;
if(typeof data13 === "string"){
if(!(formats0.test(data13))){
const err38 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
else {
const err39 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid2 = _errs36 === errors;
valid7 = valid7 || _valid2;
const _errs38 = errors;
if(data13 !== null){
const err40 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
var _valid2 = _errs38 === errors;
valid7 = valid7 || _valid2;
if(!valid7){
const err41 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
else {
errors = _errs35;
if(vErrors !== null){
if(_errs35){
vErrors.length = _errs35;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data14 = data5.runtime_profile_version_id;
const _errs41 = errors;
let valid8 = false;
const _errs42 = errors;
if(typeof data14 === "string"){
if(!(formats0.test(data14))){
const err42 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
else {
const err43 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
var _valid3 = _errs42 === errors;
valid8 = valid8 || _valid3;
const _errs44 = errors;
if(data14 !== null){
const err44 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
var _valid3 = _errs44 === errors;
valid8 = valid8 || _valid3;
if(!valid8){
const err45 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
else {
errors = _errs41;
if(vErrors !== null){
if(_errs41){
vErrors.length = _errs41;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data15 = data5.budget_usd;
const _errs47 = errors;
const _errs48 = errors;
if(!(((((((data15 === "0") || (data15 === "0.0")) || (data15 === "0.00")) || (data15 === "0.000")) || (data15 === "0.0000")) || (data15 === "0.00000")) || (data15 === "0.000000"))){
const err46 = {};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
var valid9 = _errs48 === errors;
if(valid9){
const err47 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
else {
errors = _errs47;
if(vErrors !== null){
if(_errs47){
vErrors.length = _errs47;
}
else {
vErrors = null;
}
}
}
const _errs49 = errors;
let valid10 = false;
const _errs50 = errors;
if(typeof data15 === "string"){
if(!pattern10.test(data15)){
const err48 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
else {
const err49 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
var _valid4 = _errs50 === errors;
valid10 = valid10 || _valid4;
const _errs52 = errors;
if(data15 !== null){
const err50 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
var _valid4 = _errs52 === errors;
valid10 = valid10 || _valid4;
if(!valid10){
const err51 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
else {
errors = _errs49;
if(vErrors !== null){
if(_errs49){
vErrors.length = _errs49;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data16 = data5.scenario;
if(typeof data16 !== "string"){
const err52 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
if("ctf" !== data16){
const err53 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "ctf"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
if(data5.challenge !== undefined){
let data17 = data5.challenge;
if(typeof data17 === "string"){
if(func1(data17) > 8000){
const err54 = {instancePath:instancePath+"/normalized_content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
else {
const err55 = {instancePath:instancePath+"/normalized_content/challenge",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/challenge/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data18 = data5.entry_url;
const _errs59 = errors;
let valid11 = false;
const _errs60 = errors;
if(typeof data18 === "string"){
if(func1(data18) > 2048){
const err56 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
}
else {
const err57 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
var _valid5 = _errs60 === errors;
valid11 = valid11 || _valid5;
const _errs62 = errors;
if(data18 !== null){
const err58 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
var _valid5 = _errs62 === errors;
valid11 = valid11 || _valid5;
if(!valid11){
const err59 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
else {
errors = _errs59;
if(vErrors !== null){
if(_errs59){
vErrors.length = _errs59;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err60 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CtfDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
var _valid1 = _errs16 === errors;
if(_valid1){
valid2 = true;
passing0 = 0;
var props0 = true;
}
const _errs64 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err61 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
for(const key2 in data5){
if(!(func22.call(schema83.properties, key2))){
const err62 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data19 = data5.schema_version;
if(typeof data19 !== "string"){
const err63 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
if("1.0" !== data19){
const err64 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
}
if(data5.name !== undefined){
let data20 = data5.name;
if(typeof data20 === "string"){
if(func1(data20) > 120){
const err65 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
}
else {
const err66 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
}
if(data5.objective !== undefined){
let data21 = data5.objective;
if(typeof data21 === "string"){
if(func1(data21) > 8000){
const err67 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err67];
}
else {
vErrors.push(err67);
}
errors++;
}
}
else {
const err68 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err68];
}
else {
vErrors.push(err68);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data22 = data5.starting_point;
if(typeof data22 === "string"){
if(func1(data22) > 8000){
const err69 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err69];
}
else {
vErrors.push(err69);
}
errors++;
}
}
else {
const err70 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err70];
}
else {
vErrors.push(err70);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data23 = data5.constraints;
if(typeof data23 === "string"){
if(func1(data23) > 4000){
const err71 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err71];
}
else {
vErrors.push(err71);
}
errors++;
}
}
else {
const err72 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err72];
}
else {
vErrors.push(err72);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data24 = data5.reference_ids;
if(Array.isArray(data24)){
if(data24.length > 20){
const err73 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err73];
}
else {
vErrors.push(err73);
}
errors++;
}
const len1 = data24.length;
for(let i1=0; i1<len1; i1++){
let data25 = data24[i1];
if(typeof data25 === "string"){
if(!(formats0.test(data25))){
const err74 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err74];
}
else {
vErrors.push(err74);
}
errors++;
}
}
else {
const err75 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err75];
}
else {
vErrors.push(err75);
}
errors++;
}
}
}
else {
const err76 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err76];
}
else {
vErrors.push(err76);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data26 = data5.model_profile_version_id;
const _errs83 = errors;
let valid16 = false;
const _errs84 = errors;
if(typeof data26 === "string"){
if(!(formats0.test(data26))){
const err77 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err77];
}
else {
vErrors.push(err77);
}
errors++;
}
}
else {
const err78 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err78];
}
else {
vErrors.push(err78);
}
errors++;
}
var _valid6 = _errs84 === errors;
valid16 = valid16 || _valid6;
const _errs86 = errors;
if(data26 !== null){
const err79 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err79];
}
else {
vErrors.push(err79);
}
errors++;
}
var _valid6 = _errs86 === errors;
valid16 = valid16 || _valid6;
if(!valid16){
const err80 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err80];
}
else {
vErrors.push(err80);
}
errors++;
}
else {
errors = _errs83;
if(vErrors !== null){
if(_errs83){
vErrors.length = _errs83;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data27 = data5.runtime_profile_version_id;
const _errs89 = errors;
let valid17 = false;
const _errs90 = errors;
if(typeof data27 === "string"){
if(!(formats0.test(data27))){
const err81 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err81];
}
else {
vErrors.push(err81);
}
errors++;
}
}
else {
const err82 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err82];
}
else {
vErrors.push(err82);
}
errors++;
}
var _valid7 = _errs90 === errors;
valid17 = valid17 || _valid7;
const _errs92 = errors;
if(data27 !== null){
const err83 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err83];
}
else {
vErrors.push(err83);
}
errors++;
}
var _valid7 = _errs92 === errors;
valid17 = valid17 || _valid7;
if(!valid17){
const err84 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err84];
}
else {
vErrors.push(err84);
}
errors++;
}
else {
errors = _errs89;
if(vErrors !== null){
if(_errs89){
vErrors.length = _errs89;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data28 = data5.budget_usd;
const _errs95 = errors;
const _errs96 = errors;
if(!(((((((data28 === "0") || (data28 === "0.0")) || (data28 === "0.00")) || (data28 === "0.000")) || (data28 === "0.0000")) || (data28 === "0.00000")) || (data28 === "0.000000"))){
const err85 = {};
if(vErrors === null){
vErrors = [err85];
}
else {
vErrors.push(err85);
}
errors++;
}
var valid18 = _errs96 === errors;
if(valid18){
const err86 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err86];
}
else {
vErrors.push(err86);
}
errors++;
}
else {
errors = _errs95;
if(vErrors !== null){
if(_errs95){
vErrors.length = _errs95;
}
else {
vErrors = null;
}
}
}
const _errs97 = errors;
let valid19 = false;
const _errs98 = errors;
if(typeof data28 === "string"){
if(!pattern10.test(data28)){
const err87 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err87];
}
else {
vErrors.push(err87);
}
errors++;
}
}
else {
const err88 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err88];
}
else {
vErrors.push(err88);
}
errors++;
}
var _valid8 = _errs98 === errors;
valid19 = valid19 || _valid8;
const _errs100 = errors;
if(data28 !== null){
const err89 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err89];
}
else {
vErrors.push(err89);
}
errors++;
}
var _valid8 = _errs100 === errors;
valid19 = valid19 || _valid8;
if(!valid19){
const err90 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err90];
}
else {
vErrors.push(err90);
}
errors++;
}
else {
errors = _errs97;
if(vErrors !== null){
if(_errs97){
vErrors.length = _errs97;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data29 = data5.scenario;
if(typeof data29 !== "string"){
const err91 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err91];
}
else {
vErrors.push(err91);
}
errors++;
}
if("web_single" !== data29){
const err92 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "web_single"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err92];
}
else {
vErrors.push(err92);
}
errors++;
}
}
if(data5.entry_url !== undefined){
let data30 = data5.entry_url;
const _errs105 = errors;
let valid20 = false;
const _errs106 = errors;
if(typeof data30 === "string"){
if(func1(data30) > 2048){
const err93 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err93];
}
else {
vErrors.push(err93);
}
errors++;
}
}
else {
const err94 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err94];
}
else {
vErrors.push(err94);
}
errors++;
}
var _valid9 = _errs106 === errors;
valid20 = valid20 || _valid9;
const _errs108 = errors;
if(data30 !== null){
const err95 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err95];
}
else {
vErrors.push(err95);
}
errors++;
}
var _valid9 = _errs108 === errors;
valid20 = valid20 || _valid9;
if(!valid20){
const err96 = {instancePath:instancePath+"/normalized_content/entry_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/entry_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err96];
}
else {
vErrors.push(err96);
}
errors++;
}
else {
errors = _errs105;
if(vErrors !== null){
if(_errs105){
vErrors.length = _errs105;
}
else {
vErrors = null;
}
}
}
}
if(data5.include_subdomains !== undefined){
if(typeof data5.include_subdomains !== "boolean"){
const err97 = {instancePath:instancePath+"/normalized_content/include_subdomains",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/include_subdomains/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err97];
}
else {
vErrors.push(err97);
}
errors++;
}
}
if(data5.additional_origins !== undefined){
let data32 = data5.additional_origins;
if(Array.isArray(data32)){
if(data32.length > 100){
const err98 = {instancePath:instancePath+"/normalized_content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err98];
}
else {
vErrors.push(err98);
}
errors++;
}
const len2 = data32.length;
for(let i2=0; i2<len2; i2++){
let data33 = data32[i2];
if(typeof data33 === "string"){
if(func1(data33) > 2048){
const err99 = {instancePath:instancePath+"/normalized_content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err99];
}
else {
vErrors.push(err99);
}
errors++;
}
}
else {
const err100 = {instancePath:instancePath+"/normalized_content/additional_origins/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err100];
}
else {
vErrors.push(err100);
}
errors++;
}
}
}
else {
const err101 = {instancePath:instancePath+"/normalized_content/additional_origins",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/properties/additional_origins/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err101];
}
else {
vErrors.push(err101);
}
errors++;
}
}
}
else {
const err102 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/WebDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err102];
}
else {
vErrors.push(err102);
}
errors++;
}
var _valid1 = _errs64 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 1];
}
else {
if(_valid1){
valid2 = true;
passing0 = 1;
if(props0 !== true){
props0 = true;
}
}
const _errs116 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err103 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err103];
}
else {
vErrors.push(err103);
}
errors++;
}
for(const key3 in data5){
if(!(func22.call(schema84.properties, key3))){
const err104 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key3},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err104];
}
else {
vErrors.push(err104);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data34 = data5.schema_version;
if(typeof data34 !== "string"){
const err105 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err105];
}
else {
vErrors.push(err105);
}
errors++;
}
if("1.0" !== data34){
const err106 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err106];
}
else {
vErrors.push(err106);
}
errors++;
}
}
if(data5.name !== undefined){
let data35 = data5.name;
if(typeof data35 === "string"){
if(func1(data35) > 120){
const err107 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err107];
}
else {
vErrors.push(err107);
}
errors++;
}
}
else {
const err108 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err108];
}
else {
vErrors.push(err108);
}
errors++;
}
}
if(data5.objective !== undefined){
let data36 = data5.objective;
if(typeof data36 === "string"){
if(func1(data36) > 8000){
const err109 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err109];
}
else {
vErrors.push(err109);
}
errors++;
}
}
else {
const err110 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err110];
}
else {
vErrors.push(err110);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data37 = data5.starting_point;
if(typeof data37 === "string"){
if(func1(data37) > 8000){
const err111 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err111];
}
else {
vErrors.push(err111);
}
errors++;
}
}
else {
const err112 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err112];
}
else {
vErrors.push(err112);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data38 = data5.constraints;
if(typeof data38 === "string"){
if(func1(data38) > 4000){
const err113 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err113];
}
else {
vErrors.push(err113);
}
errors++;
}
}
else {
const err114 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err114];
}
else {
vErrors.push(err114);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data39 = data5.reference_ids;
if(Array.isArray(data39)){
if(data39.length > 20){
const err115 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err115];
}
else {
vErrors.push(err115);
}
errors++;
}
const len3 = data39.length;
for(let i3=0; i3<len3; i3++){
let data40 = data39[i3];
if(typeof data40 === "string"){
if(!(formats0.test(data40))){
const err116 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err116];
}
else {
vErrors.push(err116);
}
errors++;
}
}
else {
const err117 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err117];
}
else {
vErrors.push(err117);
}
errors++;
}
}
}
else {
const err118 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err118];
}
else {
vErrors.push(err118);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data41 = data5.model_profile_version_id;
const _errs135 = errors;
let valid27 = false;
const _errs136 = errors;
if(typeof data41 === "string"){
if(!(formats0.test(data41))){
const err119 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err119];
}
else {
vErrors.push(err119);
}
errors++;
}
}
else {
const err120 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err120];
}
else {
vErrors.push(err120);
}
errors++;
}
var _valid10 = _errs136 === errors;
valid27 = valid27 || _valid10;
const _errs138 = errors;
if(data41 !== null){
const err121 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err121];
}
else {
vErrors.push(err121);
}
errors++;
}
var _valid10 = _errs138 === errors;
valid27 = valid27 || _valid10;
if(!valid27){
const err122 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err122];
}
else {
vErrors.push(err122);
}
errors++;
}
else {
errors = _errs135;
if(vErrors !== null){
if(_errs135){
vErrors.length = _errs135;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data42 = data5.runtime_profile_version_id;
const _errs141 = errors;
let valid28 = false;
const _errs142 = errors;
if(typeof data42 === "string"){
if(!(formats0.test(data42))){
const err123 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err123];
}
else {
vErrors.push(err123);
}
errors++;
}
}
else {
const err124 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err124];
}
else {
vErrors.push(err124);
}
errors++;
}
var _valid11 = _errs142 === errors;
valid28 = valid28 || _valid11;
const _errs144 = errors;
if(data42 !== null){
const err125 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err125];
}
else {
vErrors.push(err125);
}
errors++;
}
var _valid11 = _errs144 === errors;
valid28 = valid28 || _valid11;
if(!valid28){
const err126 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err126];
}
else {
vErrors.push(err126);
}
errors++;
}
else {
errors = _errs141;
if(vErrors !== null){
if(_errs141){
vErrors.length = _errs141;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data43 = data5.budget_usd;
const _errs147 = errors;
const _errs148 = errors;
if(!(((((((data43 === "0") || (data43 === "0.0")) || (data43 === "0.00")) || (data43 === "0.000")) || (data43 === "0.0000")) || (data43 === "0.00000")) || (data43 === "0.000000"))){
const err127 = {};
if(vErrors === null){
vErrors = [err127];
}
else {
vErrors.push(err127);
}
errors++;
}
var valid29 = _errs148 === errors;
if(valid29){
const err128 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err128];
}
else {
vErrors.push(err128);
}
errors++;
}
else {
errors = _errs147;
if(vErrors !== null){
if(_errs147){
vErrors.length = _errs147;
}
else {
vErrors = null;
}
}
}
const _errs149 = errors;
let valid30 = false;
const _errs150 = errors;
if(typeof data43 === "string"){
if(!pattern10.test(data43)){
const err129 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err129];
}
else {
vErrors.push(err129);
}
errors++;
}
}
else {
const err130 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err130];
}
else {
vErrors.push(err130);
}
errors++;
}
var _valid12 = _errs150 === errors;
valid30 = valid30 || _valid12;
const _errs152 = errors;
if(data43 !== null){
const err131 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err131];
}
else {
vErrors.push(err131);
}
errors++;
}
var _valid12 = _errs152 === errors;
valid30 = valid30 || _valid12;
if(!valid30){
const err132 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err132];
}
else {
vErrors.push(err132);
}
errors++;
}
else {
errors = _errs149;
if(vErrors !== null){
if(_errs149){
vErrors.length = _errs149;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data44 = data5.scenario;
if(typeof data44 !== "string"){
const err133 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err133];
}
else {
vErrors.push(err133);
}
errors++;
}
if("comprehensive" !== data44){
const err134 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "comprehensive"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err134];
}
else {
vErrors.push(err134);
}
errors++;
}
}
if(data5.assets !== undefined){
let data45 = data5.assets;
if(Array.isArray(data45)){
if(data45.length > 100){
const err135 = {instancePath:instancePath+"/normalized_content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err135];
}
else {
vErrors.push(err135);
}
errors++;
}
const len4 = data45.length;
for(let i4=0; i4<len4; i4++){
let data46 = data45[i4];
if(typeof data46 === "string"){
if(func1(data46) > 2048){
const err136 = {instancePath:instancePath+"/normalized_content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err136];
}
else {
vErrors.push(err136);
}
errors++;
}
}
else {
const err137 = {instancePath:instancePath+"/normalized_content/assets/" + i4,schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err137];
}
else {
vErrors.push(err137);
}
errors++;
}
}
}
else {
const err138 = {instancePath:instancePath+"/normalized_content/assets",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/assets/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err138];
}
else {
vErrors.push(err138);
}
errors++;
}
}
if(data5.access_notes !== undefined){
let data47 = data5.access_notes;
if(typeof data47 === "string"){
if(func1(data47) > 4000){
const err139 = {instancePath:instancePath+"/normalized_content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err139];
}
else {
vErrors.push(err139);
}
errors++;
}
}
else {
const err140 = {instancePath:instancePath+"/normalized_content/access_notes",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/properties/access_notes/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err140];
}
else {
vErrors.push(err140);
}
errors++;
}
}
}
else {
const err141 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ComprehensiveDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err141];
}
else {
vErrors.push(err141);
}
errors++;
}
var _valid1 = _errs116 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 2];
}
else {
if(_valid1){
valid2 = true;
passing0 = 2;
if(props0 !== true){
props0 = true;
}
}
const _errs162 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err142 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err142];
}
else {
vErrors.push(err142);
}
errors++;
}
for(const key4 in data5){
if(!(func22.call(schema85.properties, key4))){
const err143 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key4},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err143];
}
else {
vErrors.push(err143);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data48 = data5.schema_version;
if(typeof data48 !== "string"){
const err144 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err144];
}
else {
vErrors.push(err144);
}
errors++;
}
if("1.0" !== data48){
const err145 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err145];
}
else {
vErrors.push(err145);
}
errors++;
}
}
if(data5.name !== undefined){
let data49 = data5.name;
if(typeof data49 === "string"){
if(func1(data49) > 120){
const err146 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err146];
}
else {
vErrors.push(err146);
}
errors++;
}
}
else {
const err147 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err147];
}
else {
vErrors.push(err147);
}
errors++;
}
}
if(data5.objective !== undefined){
let data50 = data5.objective;
if(typeof data50 === "string"){
if(func1(data50) > 8000){
const err148 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err148];
}
else {
vErrors.push(err148);
}
errors++;
}
}
else {
const err149 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err149];
}
else {
vErrors.push(err149);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data51 = data5.starting_point;
if(typeof data51 === "string"){
if(func1(data51) > 8000){
const err150 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err150];
}
else {
vErrors.push(err150);
}
errors++;
}
}
else {
const err151 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err151];
}
else {
vErrors.push(err151);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data52 = data5.constraints;
if(typeof data52 === "string"){
if(func1(data52) > 4000){
const err152 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err152];
}
else {
vErrors.push(err152);
}
errors++;
}
}
else {
const err153 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err153];
}
else {
vErrors.push(err153);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data53 = data5.reference_ids;
if(Array.isArray(data53)){
if(data53.length > 20){
const err154 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err154];
}
else {
vErrors.push(err154);
}
errors++;
}
const len5 = data53.length;
for(let i5=0; i5<len5; i5++){
let data54 = data53[i5];
if(typeof data54 === "string"){
if(!(formats0.test(data54))){
const err155 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err155];
}
else {
vErrors.push(err155);
}
errors++;
}
}
else {
const err156 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i5,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err156];
}
else {
vErrors.push(err156);
}
errors++;
}
}
}
else {
const err157 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err157];
}
else {
vErrors.push(err157);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data55 = data5.model_profile_version_id;
const _errs181 = errors;
let valid37 = false;
const _errs182 = errors;
if(typeof data55 === "string"){
if(!(formats0.test(data55))){
const err158 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err158];
}
else {
vErrors.push(err158);
}
errors++;
}
}
else {
const err159 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err159];
}
else {
vErrors.push(err159);
}
errors++;
}
var _valid13 = _errs182 === errors;
valid37 = valid37 || _valid13;
const _errs184 = errors;
if(data55 !== null){
const err160 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err160];
}
else {
vErrors.push(err160);
}
errors++;
}
var _valid13 = _errs184 === errors;
valid37 = valid37 || _valid13;
if(!valid37){
const err161 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err161];
}
else {
vErrors.push(err161);
}
errors++;
}
else {
errors = _errs181;
if(vErrors !== null){
if(_errs181){
vErrors.length = _errs181;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data56 = data5.runtime_profile_version_id;
const _errs187 = errors;
let valid38 = false;
const _errs188 = errors;
if(typeof data56 === "string"){
if(!(formats0.test(data56))){
const err162 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err162];
}
else {
vErrors.push(err162);
}
errors++;
}
}
else {
const err163 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err163];
}
else {
vErrors.push(err163);
}
errors++;
}
var _valid14 = _errs188 === errors;
valid38 = valid38 || _valid14;
const _errs190 = errors;
if(data56 !== null){
const err164 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err164];
}
else {
vErrors.push(err164);
}
errors++;
}
var _valid14 = _errs190 === errors;
valid38 = valid38 || _valid14;
if(!valid38){
const err165 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err165];
}
else {
vErrors.push(err165);
}
errors++;
}
else {
errors = _errs187;
if(vErrors !== null){
if(_errs187){
vErrors.length = _errs187;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data57 = data5.budget_usd;
const _errs193 = errors;
const _errs194 = errors;
if(!(((((((data57 === "0") || (data57 === "0.0")) || (data57 === "0.00")) || (data57 === "0.000")) || (data57 === "0.0000")) || (data57 === "0.00000")) || (data57 === "0.000000"))){
const err166 = {};
if(vErrors === null){
vErrors = [err166];
}
else {
vErrors.push(err166);
}
errors++;
}
var valid39 = _errs194 === errors;
if(valid39){
const err167 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err167];
}
else {
vErrors.push(err167);
}
errors++;
}
else {
errors = _errs193;
if(vErrors !== null){
if(_errs193){
vErrors.length = _errs193;
}
else {
vErrors = null;
}
}
}
const _errs195 = errors;
let valid40 = false;
const _errs196 = errors;
if(typeof data57 === "string"){
if(!pattern10.test(data57)){
const err168 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err168];
}
else {
vErrors.push(err168);
}
errors++;
}
}
else {
const err169 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err169];
}
else {
vErrors.push(err169);
}
errors++;
}
var _valid15 = _errs196 === errors;
valid40 = valid40 || _valid15;
const _errs198 = errors;
if(data57 !== null){
const err170 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err170];
}
else {
vErrors.push(err170);
}
errors++;
}
var _valid15 = _errs198 === errors;
valid40 = valid40 || _valid15;
if(!valid40){
const err171 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err171];
}
else {
vErrors.push(err171);
}
errors++;
}
else {
errors = _errs195;
if(vErrors !== null){
if(_errs195){
vErrors.length = _errs195;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data58 = data5.scenario;
if(typeof data58 !== "string"){
const err172 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err172];
}
else {
vErrors.push(err172);
}
errors++;
}
if("exercise" !== data58){
const err173 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "exercise"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err173];
}
else {
vErrors.push(err173);
}
errors++;
}
}
if(data5.organization_name !== undefined){
let data59 = data5.organization_name;
if(typeof data59 === "string"){
if(func1(data59) > 255){
const err174 = {instancePath:instancePath+"/normalized_content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err174];
}
else {
vErrors.push(err174);
}
errors++;
}
}
else {
const err175 = {instancePath:instancePath+"/normalized_content/organization_name",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/organization_name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err175];
}
else {
vErrors.push(err175);
}
errors++;
}
}
if(data5.known_domains !== undefined){
let data60 = data5.known_domains;
if(Array.isArray(data60)){
if(data60.length > 100){
const err176 = {instancePath:instancePath+"/normalized_content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err176];
}
else {
vErrors.push(err176);
}
errors++;
}
const len6 = data60.length;
for(let i6=0; i6<len6; i6++){
let data61 = data60[i6];
if(typeof data61 === "string"){
if(func1(data61) > 253){
const err177 = {instancePath:instancePath+"/normalized_content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/maxLength",keyword:"maxLength",params:{limit: 253},message:"must NOT have more than 253 characters"};
if(vErrors === null){
vErrors = [err177];
}
else {
vErrors.push(err177);
}
errors++;
}
}
else {
const err178 = {instancePath:instancePath+"/normalized_content/known_domains/" + i6,schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err178];
}
else {
vErrors.push(err178);
}
errors++;
}
}
}
else {
const err179 = {instancePath:instancePath+"/normalized_content/known_domains",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/properties/known_domains/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err179];
}
else {
vErrors.push(err179);
}
errors++;
}
}
}
else {
const err180 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/ExerciseDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err180];
}
else {
vErrors.push(err180);
}
errors++;
}
var _valid1 = _errs162 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 3];
}
else {
if(_valid1){
valid2 = true;
passing0 = 3;
if(props0 !== true){
props0 = true;
}
}
const _errs208 = errors;
const _errs211 = errors;
const _errs212 = errors;
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
let missing0;
if(((data5.repository_url === undefined) && (missing0 = "repository_url")) || ((data5.source_reference_id === undefined) && (missing0 = "source_reference_id"))){
const err181 = {};
if(vErrors === null){
vErrors = [err181];
}
else {
vErrors.push(err181);
}
errors++;
}
else {
if(data5.repository_url !== undefined){
const _errs213 = errors;
if(typeof data5.repository_url !== "string"){
const err182 = {};
if(vErrors === null){
vErrors = [err182];
}
else {
vErrors.push(err182);
}
errors++;
}
var valid45 = _errs213 === errors;
}
else {
var valid45 = true;
}
if(valid45){
if(data5.source_reference_id !== undefined){
const _errs215 = errors;
if(typeof data5.source_reference_id !== "string"){
const err183 = {};
if(vErrors === null){
vErrors = [err183];
}
else {
vErrors.push(err183);
}
errors++;
}
var valid45 = _errs215 === errors;
}
else {
var valid45 = true;
}
}
}
}
var valid44 = _errs212 === errors;
if(valid44){
const err184 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err184];
}
else {
vErrors.push(err184);
}
errors++;
}
else {
errors = _errs211;
if(vErrors !== null){
if(_errs211){
vErrors.length = _errs211;
}
else {
vErrors = null;
}
}
}
if(data5 && typeof data5 == "object" && !Array.isArray(data5)){
if(data5.scenario === undefined){
const err185 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/required",keyword:"required",params:{missingProperty: "scenario"},message:"must have required property '"+"scenario"+"'"};
if(vErrors === null){
vErrors = [err185];
}
else {
vErrors.push(err185);
}
errors++;
}
for(const key5 in data5){
if(!(func22.call(schema86.properties, key5))){
const err186 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key5},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err186];
}
else {
vErrors.push(err186);
}
errors++;
}
}
if(data5.schema_version !== undefined){
let data64 = data5.schema_version;
if(typeof data64 !== "string"){
const err187 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err187];
}
else {
vErrors.push(err187);
}
errors++;
}
if("1.0" !== data64){
const err188 = {instancePath:instancePath+"/normalized_content/schema_version",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/schema_version/const",keyword:"const",params:{allowedValue: "1.0"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err188];
}
else {
vErrors.push(err188);
}
errors++;
}
}
if(data5.name !== undefined){
let data65 = data5.name;
if(typeof data65 === "string"){
if(func1(data65) > 120){
const err189 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/maxLength",keyword:"maxLength",params:{limit: 120},message:"must NOT have more than 120 characters"};
if(vErrors === null){
vErrors = [err189];
}
else {
vErrors.push(err189);
}
errors++;
}
}
else {
const err190 = {instancePath:instancePath+"/normalized_content/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err190];
}
else {
vErrors.push(err190);
}
errors++;
}
}
if(data5.objective !== undefined){
let data66 = data5.objective;
if(typeof data66 === "string"){
if(func1(data66) > 8000){
const err191 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err191];
}
else {
vErrors.push(err191);
}
errors++;
}
}
else {
const err192 = {instancePath:instancePath+"/normalized_content/objective",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/objective/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err192];
}
else {
vErrors.push(err192);
}
errors++;
}
}
if(data5.starting_point !== undefined){
let data67 = data5.starting_point;
if(typeof data67 === "string"){
if(func1(data67) > 8000){
const err193 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/maxLength",keyword:"maxLength",params:{limit: 8000},message:"must NOT have more than 8000 characters"};
if(vErrors === null){
vErrors = [err193];
}
else {
vErrors.push(err193);
}
errors++;
}
}
else {
const err194 = {instancePath:instancePath+"/normalized_content/starting_point",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/starting_point/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err194];
}
else {
vErrors.push(err194);
}
errors++;
}
}
if(data5.constraints !== undefined){
let data68 = data5.constraints;
if(typeof data68 === "string"){
if(func1(data68) > 4000){
const err195 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/maxLength",keyword:"maxLength",params:{limit: 4000},message:"must NOT have more than 4000 characters"};
if(vErrors === null){
vErrors = [err195];
}
else {
vErrors.push(err195);
}
errors++;
}
}
else {
const err196 = {instancePath:instancePath+"/normalized_content/constraints",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/constraints/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err196];
}
else {
vErrors.push(err196);
}
errors++;
}
}
if(data5.reference_ids !== undefined){
let data69 = data5.reference_ids;
if(Array.isArray(data69)){
if(data69.length > 20){
const err197 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/maxItems",keyword:"maxItems",params:{limit: 20},message:"must NOT have more than 20 items"};
if(vErrors === null){
vErrors = [err197];
}
else {
vErrors.push(err197);
}
errors++;
}
const len7 = data69.length;
for(let i7=0; i7<len7; i7++){
let data70 = data69[i7];
if(typeof data70 === "string"){
if(!(formats0.test(data70))){
const err198 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err198];
}
else {
vErrors.push(err198);
}
errors++;
}
}
else {
const err199 = {instancePath:instancePath+"/normalized_content/reference_ids/" + i7,schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err199];
}
else {
vErrors.push(err199);
}
errors++;
}
}
}
else {
const err200 = {instancePath:instancePath+"/normalized_content/reference_ids",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/reference_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err200];
}
else {
vErrors.push(err200);
}
errors++;
}
}
if(data5.model_profile_version_id !== undefined){
let data71 = data5.model_profile_version_id;
const _errs233 = errors;
let valid49 = false;
const _errs234 = errors;
if(typeof data71 === "string"){
if(!(formats0.test(data71))){
const err201 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err201];
}
else {
vErrors.push(err201);
}
errors++;
}
}
else {
const err202 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err202];
}
else {
vErrors.push(err202);
}
errors++;
}
var _valid16 = _errs234 === errors;
valid49 = valid49 || _valid16;
const _errs236 = errors;
if(data71 !== null){
const err203 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err203];
}
else {
vErrors.push(err203);
}
errors++;
}
var _valid16 = _errs236 === errors;
valid49 = valid49 || _valid16;
if(!valid49){
const err204 = {instancePath:instancePath+"/normalized_content/model_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/model_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err204];
}
else {
vErrors.push(err204);
}
errors++;
}
else {
errors = _errs233;
if(vErrors !== null){
if(_errs233){
vErrors.length = _errs233;
}
else {
vErrors = null;
}
}
}
}
if(data5.runtime_profile_version_id !== undefined){
let data72 = data5.runtime_profile_version_id;
const _errs239 = errors;
let valid50 = false;
const _errs240 = errors;
if(typeof data72 === "string"){
if(!(formats0.test(data72))){
const err205 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err205];
}
else {
vErrors.push(err205);
}
errors++;
}
}
else {
const err206 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err206];
}
else {
vErrors.push(err206);
}
errors++;
}
var _valid17 = _errs240 === errors;
valid50 = valid50 || _valid17;
const _errs242 = errors;
if(data72 !== null){
const err207 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err207];
}
else {
vErrors.push(err207);
}
errors++;
}
var _valid17 = _errs242 === errors;
valid50 = valid50 || _valid17;
if(!valid50){
const err208 = {instancePath:instancePath+"/normalized_content/runtime_profile_version_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/runtime_profile_version_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err208];
}
else {
vErrors.push(err208);
}
errors++;
}
else {
errors = _errs239;
if(vErrors !== null){
if(_errs239){
vErrors.length = _errs239;
}
else {
vErrors = null;
}
}
}
}
if(data5.budget_usd !== undefined){
let data73 = data5.budget_usd;
const _errs245 = errors;
const _errs246 = errors;
if(!(((((((data73 === "0") || (data73 === "0.0")) || (data73 === "0.00")) || (data73 === "0.000")) || (data73 === "0.0000")) || (data73 === "0.00000")) || (data73 === "0.000000"))){
const err209 = {};
if(vErrors === null){
vErrors = [err209];
}
else {
vErrors.push(err209);
}
errors++;
}
var valid51 = _errs246 === errors;
if(valid51){
const err210 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/not",keyword:"not",params:{},message:"must NOT be valid"};
if(vErrors === null){
vErrors = [err210];
}
else {
vErrors.push(err210);
}
errors++;
}
else {
errors = _errs245;
if(vErrors !== null){
if(_errs245){
vErrors.length = _errs245;
}
else {
vErrors = null;
}
}
}
const _errs247 = errors;
let valid52 = false;
const _errs248 = errors;
if(typeof data73 === "string"){
if(!pattern10.test(data73)){
const err211 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/pattern",keyword:"pattern",params:{pattern: "^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"},message:"must match pattern \""+"^(0|[1-9][0-9]{0,11})(\\.[0-9]{1,6})?$"+"\""};
if(vErrors === null){
vErrors = [err211];
}
else {
vErrors.push(err211);
}
errors++;
}
}
else {
const err212 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err212];
}
else {
vErrors.push(err212);
}
errors++;
}
var _valid18 = _errs248 === errors;
valid52 = valid52 || _valid18;
const _errs250 = errors;
if(data73 !== null){
const err213 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err213];
}
else {
vErrors.push(err213);
}
errors++;
}
var _valid18 = _errs250 === errors;
valid52 = valid52 || _valid18;
if(!valid52){
const err214 = {instancePath:instancePath+"/normalized_content/budget_usd",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/budget_usd/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err214];
}
else {
vErrors.push(err214);
}
errors++;
}
else {
errors = _errs247;
if(vErrors !== null){
if(_errs247){
vErrors.length = _errs247;
}
else {
vErrors = null;
}
}
}
}
if(data5.scenario !== undefined){
let data74 = data5.scenario;
if(typeof data74 !== "string"){
const err215 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err215];
}
else {
vErrors.push(err215);
}
errors++;
}
if("code_audit" !== data74){
const err216 = {instancePath:instancePath+"/normalized_content/scenario",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/scenario/const",keyword:"const",params:{allowedValue: "code_audit"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err216];
}
else {
vErrors.push(err216);
}
errors++;
}
}
if(data5.repository_url !== undefined){
let data75 = data5.repository_url;
const _errs255 = errors;
let valid53 = false;
const _errs256 = errors;
if(typeof data75 === "string"){
if(func1(data75) > 2048){
const err217 = {instancePath:instancePath+"/normalized_content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 2048},message:"must NOT have more than 2048 characters"};
if(vErrors === null){
vErrors = [err217];
}
else {
vErrors.push(err217);
}
errors++;
}
}
else {
const err218 = {instancePath:instancePath+"/normalized_content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err218];
}
else {
vErrors.push(err218);
}
errors++;
}
var _valid19 = _errs256 === errors;
valid53 = valid53 || _valid19;
const _errs258 = errors;
if(data75 !== null){
const err219 = {instancePath:instancePath+"/normalized_content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err219];
}
else {
vErrors.push(err219);
}
errors++;
}
var _valid19 = _errs258 === errors;
valid53 = valid53 || _valid19;
if(!valid53){
const err220 = {instancePath:instancePath+"/normalized_content/repository_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/repository_url/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err220];
}
else {
vErrors.push(err220);
}
errors++;
}
else {
errors = _errs255;
if(vErrors !== null){
if(_errs255){
vErrors.length = _errs255;
}
else {
vErrors = null;
}
}
}
}
if(data5.source_reference_id !== undefined){
let data76 = data5.source_reference_id;
const _errs261 = errors;
let valid54 = false;
const _errs262 = errors;
if(typeof data76 === "string"){
if(!(formats0.test(data76))){
const err221 = {instancePath:instancePath+"/normalized_content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err221];
}
else {
vErrors.push(err221);
}
errors++;
}
}
else {
const err222 = {instancePath:instancePath+"/normalized_content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err222];
}
else {
vErrors.push(err222);
}
errors++;
}
var _valid20 = _errs262 === errors;
valid54 = valid54 || _valid20;
const _errs264 = errors;
if(data76 !== null){
const err223 = {instancePath:instancePath+"/normalized_content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err223];
}
else {
vErrors.push(err223);
}
errors++;
}
var _valid20 = _errs264 === errors;
valid54 = valid54 || _valid20;
if(!valid54){
const err224 = {instancePath:instancePath+"/normalized_content/source_reference_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/source_reference_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err224];
}
else {
vErrors.push(err224);
}
errors++;
}
else {
errors = _errs261;
if(vErrors !== null){
if(_errs261){
vErrors.length = _errs261;
}
else {
vErrors = null;
}
}
}
}
if(data5.revision !== undefined){
let data77 = data5.revision;
const _errs267 = errors;
let valid55 = false;
const _errs268 = errors;
if(typeof data77 === "string"){
if(func1(data77) > 255){
const err225 = {instancePath:instancePath+"/normalized_content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/maxLength",keyword:"maxLength",params:{limit: 255},message:"must NOT have more than 255 characters"};
if(vErrors === null){
vErrors = [err225];
}
else {
vErrors.push(err225);
}
errors++;
}
}
else {
const err226 = {instancePath:instancePath+"/normalized_content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err226];
}
else {
vErrors.push(err226);
}
errors++;
}
var _valid21 = _errs268 === errors;
valid55 = valid55 || _valid21;
const _errs270 = errors;
if(data77 !== null){
const err227 = {instancePath:instancePath+"/normalized_content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err227];
}
else {
vErrors.push(err227);
}
errors++;
}
var _valid21 = _errs270 === errors;
valid55 = valid55 || _valid21;
if(!valid55){
const err228 = {instancePath:instancePath+"/normalized_content/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/properties/revision/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err228];
}
else {
vErrors.push(err228);
}
errors++;
}
else {
errors = _errs267;
if(vErrors !== null){
if(_errs267){
vErrors.length = _errs267;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err229 = {instancePath:instancePath+"/normalized_content",schemaPath:"urn:wuji:contracts:0.5#/$defs/CodeAuditDraft/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err229];
}
else {
vErrors.push(err229);
}
errors++;
}
var _valid1 = _errs208 === errors;
if(_valid1 && valid2){
valid2 = false;
passing0 = [passing0, 4];
}
else {
if(_valid1){
valid2 = true;
passing0 = 4;
if(props0 !== true){
props0 = true;
}
}
}
}
}
}
if(!valid2){
const err230 = {instancePath:instancePath+"/normalized_content",schemaPath:"#/properties/normalized_content/anyOf/0/oneOf",keyword:"oneOf",params:{passingSchemas: passing0},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err230];
}
else {
vErrors.push(err230);
}
errors++;
}
else {
errors = _errs15;
if(vErrors !== null){
if(_errs15){
vErrors.length = _errs15;
}
else {
vErrors = null;
}
}
}
var _valid0 = _errs14 === errors;
valid1 = valid1 || _valid0;
const _errs272 = errors;
const _errs273 = errors;
let valid56 = false;
let passing1 = null;
const _errs274 = errors;
if(!(validate40(data5, {instancePath:instancePath+"/normalized_content",parentData:data,parentDataProperty:"normalized_content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate40.errors : vErrors.concat(validate40.errors);
errors = vErrors.length;
}
var _valid22 = _errs274 === errors;
if(_valid22){
valid56 = true;
passing1 = 0;
var props1 = true;
}
const _errs275 = errors;
if(!(validate42(data5, {instancePath:instancePath+"/normalized_content",parentData:data,parentDataProperty:"normalized_content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate42.errors : vErrors.concat(validate42.errors);
errors = vErrors.length;
}
var _valid22 = _errs275 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 1];
}
else {
if(_valid22){
valid56 = true;
passing1 = 1;
if(props1 !== true){
props1 = true;
}
}
const _errs276 = errors;
if(!(validate50(data5, {instancePath:instancePath+"/normalized_content",parentData:data,parentDataProperty:"normalized_content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate50.errors : vErrors.concat(validate50.errors);
errors = vErrors.length;
}
var _valid22 = _errs276 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 2];
}
else {
if(_valid22){
valid56 = true;
passing1 = 2;
if(props1 !== true){
props1 = true;
}
}
const _errs277 = errors;
if(!(validate52(data5, {instancePath:instancePath+"/normalized_content",parentData:data,parentDataProperty:"normalized_content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate52.errors : vErrors.concat(validate52.errors);
errors = vErrors.length;
}
var _valid22 = _errs277 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 3];
}
else {
if(_valid22){
valid56 = true;
passing1 = 3;
if(props1 !== true){
props1 = true;
}
}
const _errs278 = errors;
if(!(validate54(data5, {instancePath:instancePath+"/normalized_content",parentData:data,parentDataProperty:"normalized_content",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate54.errors : vErrors.concat(validate54.errors);
errors = vErrors.length;
}
var _valid22 = _errs278 === errors;
if(_valid22 && valid56){
valid56 = false;
passing1 = [passing1, 4];
}
else {
if(_valid22){
valid56 = true;
passing1 = 4;
if(props1 !== true){
props1 = true;
}
}
}
}
}
}
if(!valid56){
const err231 = {instancePath:instancePath+"/normalized_content",schemaPath:"#/properties/normalized_content/anyOf/1/oneOf",keyword:"oneOf",params:{passingSchemas: passing1},message:"must match exactly one schema in oneOf"};
if(vErrors === null){
vErrors = [err231];
}
else {
vErrors.push(err231);
}
errors++;
}
else {
errors = _errs273;
if(vErrors !== null){
if(_errs273){
vErrors.length = _errs273;
}
else {
vErrors = null;
}
}
}
var _valid0 = _errs272 === errors;
valid1 = valid1 || _valid0;
if(_valid0){
if(props0 !== true && props1 !== undefined){
if(props1 === true){
props0 = true;
}
else {
props0 = props0 || {};
Object.assign(props0, props1);
}
}
}
if(!valid1){
const err232 = {instancePath:instancePath+"/normalized_content",schemaPath:"#/properties/normalized_content/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err232];
}
else {
vErrors.push(err232);
}
errors++;
}
else {
errors = _errs13;
if(vErrors !== null){
if(_errs13){
vErrors.length = _errs13;
}
else {
vErrors = null;
}
}
}
}
if(data.model_snapshot !== undefined){
let data78 = data.model_snapshot;
const _errs280 = errors;
let valid57 = false;
const _errs281 = errors;
if(!(validate57(data78, {instancePath:instancePath+"/model_snapshot",parentData:data,parentDataProperty:"model_snapshot",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate57.errors : vErrors.concat(validate57.errors);
errors = vErrors.length;
}
var _valid23 = _errs281 === errors;
valid57 = valid57 || _valid23;
const _errs282 = errors;
if(data78 !== null){
const err233 = {instancePath:instancePath+"/model_snapshot",schemaPath:"#/properties/model_snapshot/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err233];
}
else {
vErrors.push(err233);
}
errors++;
}
var _valid23 = _errs282 === errors;
valid57 = valid57 || _valid23;
if(!valid57){
const err234 = {instancePath:instancePath+"/model_snapshot",schemaPath:"#/properties/model_snapshot/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err234];
}
else {
vErrors.push(err234);
}
errors++;
}
else {
errors = _errs280;
if(vErrors !== null){
if(_errs280){
vErrors.length = _errs280;
}
else {
vErrors = null;
}
}
}
}
if(data.input_digest !== undefined){
if(typeof data.input_digest !== "string"){
const err235 = {instancePath:instancePath+"/input_digest",schemaPath:"#/properties/input_digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err235];
}
else {
vErrors.push(err235);
}
errors++;
}
}
if(data.authorization_digest !== undefined){
if(typeof data.authorization_digest !== "string"){
const err236 = {instancePath:instancePath+"/authorization_digest",schemaPath:"#/properties/authorization_digest/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err236];
}
else {
vErrors.push(err236);
}
errors++;
}
}
if(data.can_create !== undefined){
if(typeof data.can_create !== "boolean"){
const err237 = {instancePath:instancePath+"/can_create",schemaPath:"#/properties/can_create/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err237];
}
else {
vErrors.push(err237);
}
errors++;
}
}
if(data.blockers !== undefined){
let data82 = data.blockers;
if(Array.isArray(data82)){
const len8 = data82.length;
for(let i8=0; i8<len8; i8++){
let data83 = data82[i8];
if(data83 && typeof data83 == "object" && !Array.isArray(data83)){
if(data83.code === undefined){
const err238 = {instancePath:instancePath+"/blockers/" + i8,schemaPath:"urn:wuji:contracts:0.5#/$defs/CreationBlocker/required",keyword:"required",params:{missingProperty: "code"},message:"must have required property '"+"code"+"'"};
if(vErrors === null){
vErrors = [err238];
}
else {
vErrors.push(err238);
}
errors++;
}
if(data83.message === undefined){
const err239 = {instancePath:instancePath+"/blockers/" + i8,schemaPath:"urn:wuji:contracts:0.5#/$defs/CreationBlocker/required",keyword:"required",params:{missingProperty: "message"},message:"must have required property '"+"message"+"'"};
if(vErrors === null){
vErrors = [err239];
}
else {
vErrors.push(err239);
}
errors++;
}
if(data83.code !== undefined){
if(typeof data83.code !== "string"){
const err240 = {instancePath:instancePath+"/blockers/" + i8+"/code",schemaPath:"urn:wuji:contracts:0.5#/$defs/CreationBlocker/properties/code/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err240];
}
else {
vErrors.push(err240);
}
errors++;
}
}
if(data83.message !== undefined){
if(typeof data83.message !== "string"){
const err241 = {instancePath:instancePath+"/blockers/" + i8+"/message",schemaPath:"urn:wuji:contracts:0.5#/$defs/CreationBlocker/properties/message/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err241];
}
else {
vErrors.push(err241);
}
errors++;
}
}
}
else {
const err242 = {instancePath:instancePath+"/blockers/" + i8,schemaPath:"urn:wuji:contracts:0.5#/$defs/CreationBlocker/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err242];
}
else {
vErrors.push(err242);
}
errors++;
}
}
}
else {
const err243 = {instancePath:instancePath+"/blockers",schemaPath:"#/properties/blockers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err243];
}
else {
vErrors.push(err243);
}
errors++;
}
}
if(data.created_at !== undefined){
let data86 = data.created_at;
if(typeof data86 === "string"){
if(!(formats2.validate(data86))){
const err244 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err244];
}
else {
vErrors.push(err244);
}
errors++;
}
}
else {
const err245 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err245];
}
else {
vErrors.push(err245);
}
errors++;
}
}
if(data.expires_at !== undefined){
let data87 = data.expires_at;
if(typeof data87 === "string"){
if(!(formats2.validate(data87))){
const err246 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err246];
}
else {
vErrors.push(err246);
}
errors++;
}
}
else {
const err247 = {instancePath:instancePath+"/expires_at",schemaPath:"#/properties/expires_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err247];
}
else {
vErrors.push(err247);
}
errors++;
}
}
}
else {
const err248 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err248];
}
else {
vErrors.push(err248);
}
errors++;
}
validate89.errors = vErrors;
return errors === 0;
}
validate89.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateAgentRunPage = validate96;
const schema106 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/AgentRun"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"AgentRunPage","type":"object"};
const schema107 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"phase":{"enum":["bootstrap","reason","explore"],"title":"Phase","type":"string"},"intent_id":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Intent Id"},"worker_profile_id":{"title":"Worker Profile Id","type":"string"},"state":{"title":"State","type":"string"},"result_state":{"title":"Result State","type":"string"},"outcome":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Outcome"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","phase","intent_id","worker_profile_id","state","result_state","outcome","created_at","updated_at"],"title":"AgentRun","type":"object"};

function validate96(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate96.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.phase === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "phase"},message:"must have required property '"+"phase"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.intent_id === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "intent_id"},message:"must have required property '"+"intent_id"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.worker_profile_id === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "worker_profile_id"},message:"must have required property '"+"worker_profile_id"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.state === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data1.result_state === undefined){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "result_state"},message:"must have required property '"+"result_state"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data1.outcome === undefined){
const err10 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "outcome"},message:"must have required property '"+"outcome"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data1.created_at === undefined){
const err11 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data1.updated_at === undefined){
const err12 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
for(const key1 in data1){
if(!(func22.call(schema107.properties, key1))){
const err13 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err14 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data1.phase !== undefined){
let data3 = data1.phase;
if(typeof data3 !== "string"){
const err16 = {instancePath:instancePath+"/items/" + i0+"/phase",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/phase/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(!(((data3 === "bootstrap") || (data3 === "reason")) || (data3 === "explore"))){
const err17 = {instancePath:instancePath+"/items/" + i0+"/phase",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/phase/enum",keyword:"enum",params:{allowedValues: schema107.properties.phase.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data1.intent_id !== undefined){
let data4 = data1.intent_id;
const _errs13 = errors;
let valid5 = false;
const _errs14 = errors;
if(typeof data4 !== "string"){
const err18 = {instancePath:instancePath+"/items/" + i0+"/intent_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/intent_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
var _valid0 = _errs14 === errors;
valid5 = valid5 || _valid0;
const _errs16 = errors;
if(data4 !== null){
const err19 = {instancePath:instancePath+"/items/" + i0+"/intent_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/intent_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
var _valid0 = _errs16 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err20 = {instancePath:instancePath+"/items/" + i0+"/intent_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/intent_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
else {
errors = _errs13;
if(vErrors !== null){
if(_errs13){
vErrors.length = _errs13;
}
else {
vErrors = null;
}
}
}
}
if(data1.worker_profile_id !== undefined){
if(typeof data1.worker_profile_id !== "string"){
const err21 = {instancePath:instancePath+"/items/" + i0+"/worker_profile_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/worker_profile_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data1.state !== undefined){
if(typeof data1.state !== "string"){
const err22 = {instancePath:instancePath+"/items/" + i0+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data1.result_state !== undefined){
if(typeof data1.result_state !== "string"){
const err23 = {instancePath:instancePath+"/items/" + i0+"/result_state",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/result_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data1.outcome !== undefined){
let data8 = data1.outcome;
const _errs25 = errors;
let valid6 = false;
const _errs26 = errors;
if(typeof data8 !== "string"){
const err24 = {instancePath:instancePath+"/items/" + i0+"/outcome",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/outcome/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
var _valid1 = _errs26 === errors;
valid6 = valid6 || _valid1;
const _errs28 = errors;
if(data8 !== null){
const err25 = {instancePath:instancePath+"/items/" + i0+"/outcome",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/outcome/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
var _valid1 = _errs28 === errors;
valid6 = valid6 || _valid1;
if(!valid6){
const err26 = {instancePath:instancePath+"/items/" + i0+"/outcome",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/outcome/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
else {
errors = _errs25;
if(vErrors !== null){
if(_errs25){
vErrors.length = _errs25;
}
else {
vErrors = null;
}
}
}
}
if(data1.created_at !== undefined){
let data9 = data1.created_at;
if(typeof data9 === "string"){
if(!(formats2.validate(data9))){
const err27 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
if(data1.updated_at !== undefined){
let data10 = data1.updated_at;
if(typeof data10 === "string"){
if(!(formats2.validate(data10))){
const err29 = {instancePath:instancePath+"/items/" + i0+"/updated_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
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
const err30 = {instancePath:instancePath+"/items/" + i0+"/updated_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
}
else {
const err31 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/AgentRun/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
const err32 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data11 = data.next_cursor;
const _errs35 = errors;
let valid7 = false;
const _errs36 = errors;
if(typeof data11 !== "string"){
const err33 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
var _valid2 = _errs36 === errors;
valid7 = valid7 || _valid2;
const _errs38 = errors;
if(data11 !== null){
const err34 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid2 = _errs38 === errors;
valid7 = valid7 || _valid2;
if(!valid7){
const err35 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
else {
errors = _errs35;
if(vErrors !== null){
if(_errs35){
vErrors.length = _errs35;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err36 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
validate96.errors = vErrors;
return errors === 0;
}
validate96.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateToolCallPage = validate97;
const schema108 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/ToolCall"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"ToolCallPage","type":"object"};
const schema109 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"agent_run_id":{"format":"uuid","title":"Agent Run Id","type":"string"},"tool":{"title":"Tool","type":"string"},"state":{"title":"State","type":"string"},"args":{"additionalProperties":true,"title":"Args","type":"object"},"result":{"anyOf":[{"additionalProperties":true,"type":"object"},{"type":"null"}],"title":"Result"},"cancel_requested":{"title":"Cancel Requested","type":"boolean"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"updated_at":{"format":"date-time","title":"Updated At","type":"string"}},"required":["id","agent_run_id","tool","state","args","result","cancel_requested","created_at","updated_at"],"title":"ToolCall","type":"object"};

function validate97(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate97.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.agent_run_id === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "agent_run_id"},message:"must have required property '"+"agent_run_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.tool === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "tool"},message:"must have required property '"+"tool"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.state === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.args === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "args"},message:"must have required property '"+"args"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data1.result === undefined){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "result"},message:"must have required property '"+"result"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data1.cancel_requested === undefined){
const err10 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "cancel_requested"},message:"must have required property '"+"cancel_requested"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data1.created_at === undefined){
const err11 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data1.updated_at === undefined){
const err12 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/required",keyword:"required",params:{missingProperty: "updated_at"},message:"must have required property '"+"updated_at"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
for(const key1 in data1){
if(!(func22.call(schema109.properties, key1))){
const err13 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err14 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data1.agent_run_id !== undefined){
let data3 = data1.agent_run_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err16 = {instancePath:instancePath+"/items/" + i0+"/agent_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/agent_run_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err17 = {instancePath:instancePath+"/items/" + i0+"/agent_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/agent_run_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data1.tool !== undefined){
if(typeof data1.tool !== "string"){
const err18 = {instancePath:instancePath+"/items/" + i0+"/tool",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/tool/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data1.state !== undefined){
if(typeof data1.state !== "string"){
const err19 = {instancePath:instancePath+"/items/" + i0+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data1.args !== undefined){
let data6 = data1.args;
if(data6 && typeof data6 == "object" && !Array.isArray(data6)){
}
else {
const err20 = {instancePath:instancePath+"/items/" + i0+"/args",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/args/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data1.result !== undefined){
let data7 = data1.result;
const _errs20 = errors;
let valid5 = false;
const _errs21 = errors;
if(data7 && typeof data7 == "object" && !Array.isArray(data7)){
}
else {
const err21 = {instancePath:instancePath+"/items/" + i0+"/result",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/result/anyOf/0/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
var _valid0 = _errs21 === errors;
valid5 = valid5 || _valid0;
const _errs24 = errors;
if(data7 !== null){
const err22 = {instancePath:instancePath+"/items/" + i0+"/result",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/result/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
var _valid0 = _errs24 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err23 = {instancePath:instancePath+"/items/" + i0+"/result",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/result/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
else {
errors = _errs20;
if(vErrors !== null){
if(_errs20){
vErrors.length = _errs20;
}
else {
vErrors = null;
}
}
}
}
if(data1.cancel_requested !== undefined){
if(typeof data1.cancel_requested !== "boolean"){
const err24 = {instancePath:instancePath+"/items/" + i0+"/cancel_requested",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/cancel_requested/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data1.created_at !== undefined){
let data9 = data1.created_at;
if(typeof data9 === "string"){
if(!(formats2.validate(data9))){
const err25 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
else {
const err26 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data1.updated_at !== undefined){
let data10 = data1.updated_at;
if(typeof data10 === "string"){
if(!(formats2.validate(data10))){
const err27 = {instancePath:instancePath+"/items/" + i0+"/updated_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/updated_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/items/" + i0+"/updated_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/properties/updated_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
}
else {
const err29 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/ToolCall/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
}
else {
const err30 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data11 = data.next_cursor;
const _errs33 = errors;
let valid6 = false;
const _errs34 = errors;
if(typeof data11 !== "string"){
const err31 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid6 = valid6 || _valid1;
const _errs36 = errors;
if(data11 !== null){
const err32 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid6 = valid6 || _valid1;
if(!valid6){
const err33 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
else {
errors = _errs33;
if(vErrors !== null){
if(_errs33){
vErrors.length = _errs33;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err34 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
validate97.errors = vErrors;
return errors === 0;
}
validate97.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateArtifactPage = validate98;
const schema110 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Artifact"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"ArtifactPage","type":"object"};
const schema111 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"tool_call_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"title":"Tool Call Id"},"kind":{"title":"Kind","type":"string"},"name":{"title":"Name","type":"string"},"mime":{"title":"Mime","type":"string"},"size":{"minimum":0,"title":"Size","type":"integer"},"sha256":{"title":"Sha256","type":"string"},"state":{"title":"State","type":"string"},"created_at":{"format":"date-time","title":"Created At","type":"string"}},"required":["id","tool_call_id","kind","name","mime","size","sha256","state","created_at"],"title":"Artifact","type":"object"};

function validate98(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate98.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.tool_call_id === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "tool_call_id"},message:"must have required property '"+"tool_call_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.kind === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "kind"},message:"must have required property '"+"kind"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.name === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "name"},message:"must have required property '"+"name"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.mime === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "mime"},message:"must have required property '"+"mime"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data1.size === undefined){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "size"},message:"must have required property '"+"size"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data1.sha256 === undefined){
const err10 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "sha256"},message:"must have required property '"+"sha256"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data1.state === undefined){
const err11 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data1.created_at === undefined){
const err12 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
for(const key1 in data1){
if(!(func22.call(schema111.properties, key1))){
const err13 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err14 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data1.tool_call_id !== undefined){
let data3 = data1.tool_call_id;
const _errs11 = errors;
let valid5 = false;
const _errs12 = errors;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err16 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/tool_call_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err17 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/tool_call_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid0 = _errs12 === errors;
valid5 = valid5 || _valid0;
const _errs14 = errors;
if(data3 !== null){
const err18 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/tool_call_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
var _valid0 = _errs14 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err19 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/tool_call_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
else {
errors = _errs11;
if(vErrors !== null){
if(_errs11){
vErrors.length = _errs11;
}
else {
vErrors = null;
}
}
}
}
if(data1.kind !== undefined){
if(typeof data1.kind !== "string"){
const err20 = {instancePath:instancePath+"/items/" + i0+"/kind",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/kind/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
}
if(data1.name !== undefined){
if(typeof data1.name !== "string"){
const err21 = {instancePath:instancePath+"/items/" + i0+"/name",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/name/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data1.mime !== undefined){
if(typeof data1.mime !== "string"){
const err22 = {instancePath:instancePath+"/items/" + i0+"/mime",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/mime/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data1.size !== undefined){
let data7 = data1.size;
if(!(((typeof data7 == "number") && (!(data7 % 1) && !isNaN(data7))) && (isFinite(data7)))){
const err23 = {instancePath:instancePath+"/items/" + i0+"/size",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/size/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
if((typeof data7 == "number") && (isFinite(data7))){
if(data7 < 0 || isNaN(data7)){
const err24 = {instancePath:instancePath+"/items/" + i0+"/size",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/size/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
}
if(data1.sha256 !== undefined){
if(typeof data1.sha256 !== "string"){
const err25 = {instancePath:instancePath+"/items/" + i0+"/sha256",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data1.state !== undefined){
if(typeof data1.state !== "string"){
const err26 = {instancePath:instancePath+"/items/" + i0+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data1.created_at !== undefined){
let data10 = data1.created_at;
if(typeof data10 === "string"){
if(!(formats2.validate(data10))){
const err27 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
else {
const err28 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
}
else {
const err29 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Artifact/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
}
else {
const err30 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data11 = data.next_cursor;
const _errs31 = errors;
let valid6 = false;
const _errs32 = errors;
if(typeof data11 !== "string"){
const err31 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
var _valid1 = _errs32 === errors;
valid6 = valid6 || _valid1;
const _errs34 = errors;
if(data11 !== null){
const err32 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
var _valid1 = _errs34 === errors;
valid6 = valid6 || _valid1;
if(!valid6){
const err33 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
else {
errors = _errs31;
if(vErrors !== null){
if(_errs31){
vErrors.length = _errs31;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err34 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
validate98.errors = vErrors;
return errors === 0;
}
validate98.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateBlackBoardSnapshot = validate99;
const schema112 = {"additionalProperties":false,"properties":{"state":{"enum":["pending","available"],"title":"State","type":"string"},"native_project_id":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Native Project Id"},"graph":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/NativeGraph"},{"type":"null"}]},"captured_at":{"anyOf":[{"format":"date-time","type":"string"},{"type":"null"}],"title":"Captured At"},"digest":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Digest"}},"required":["state","native_project_id","graph","captured_at","digest"],"title":"BlackBoardSnapshot","type":"object"};
const schema113 = {"additionalProperties":false,"properties":{"project":{"additionalProperties":true,"title":"Project","type":"object"},"facts":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/GraphFact"},"title":"Facts","type":"array"},"intents":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/GraphIntent"},"title":"Intents","type":"array"},"hints":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/GraphHint"},"title":"Hints","type":"array"}},"required":["project","facts","intents","hints"],"title":"NativeGraph","type":"object"};
const schema114 = {"additionalProperties":false,"properties":{"id":{"title":"Id","type":"string"},"description":{"title":"Description","type":"string"}},"required":["id","description"],"title":"GraphFact","type":"object"};
const schema115 = {"additionalProperties":false,"properties":{"id":{"title":"Id","type":"string"},"from":{"items":{"type":"string"},"title":"From","type":"array"},"to":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"To"},"description":{"title":"Description","type":"string"},"creator":{"title":"Creator","type":"string"},"worker":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Worker"},"last_heartbeat_at":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Last Heartbeat At"},"created_at":{"title":"Created At","type":"string"},"concluded_at":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Concluded At"}},"required":["id","from","to","description","creator","worker","last_heartbeat_at","created_at","concluded_at"],"title":"GraphIntent","type":"object"};
const schema116 = {"additionalProperties":false,"properties":{"id":{"title":"Id","type":"string"},"content":{"title":"Content","type":"string"},"creator":{"title":"Creator","type":"string"},"created_at":{"title":"Created At","type":"string"}},"required":["id","content","creator","created_at"],"title":"GraphHint","type":"object"};

function validate100(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate100.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.project === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "project"},message:"must have required property '"+"project"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.facts === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "facts"},message:"must have required property '"+"facts"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.intents === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "intents"},message:"must have required property '"+"intents"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.hints === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "hints"},message:"must have required property '"+"hints"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
for(const key0 in data){
if(!((((key0 === "project") || (key0 === "facts")) || (key0 === "intents")) || (key0 === "hints"))){
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
if(data.project !== undefined){
let data0 = data.project;
if(data0 && typeof data0 == "object" && !Array.isArray(data0)){
}
else {
const err5 = {instancePath:instancePath+"/project",schemaPath:"#/properties/project/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
}
if(data.facts !== undefined){
let data1 = data.facts;
if(Array.isArray(data1)){
const len0 = data1.length;
for(let i0=0; i0<len0; i0++){
let data2 = data1[i0];
if(data2 && typeof data2 == "object" && !Array.isArray(data2)){
if(data2.id === undefined){
const err6 = {instancePath:instancePath+"/facts/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data2.description === undefined){
const err7 = {instancePath:instancePath+"/facts/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/required",keyword:"required",params:{missingProperty: "description"},message:"must have required property '"+"description"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key1 in data2){
if(!((key1 === "id") || (key1 === "description"))){
const err8 = {instancePath:instancePath+"/facts/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
}
if(data2.id !== undefined){
if(typeof data2.id !== "string"){
const err9 = {instancePath:instancePath+"/facts/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data2.description !== undefined){
if(typeof data2.description !== "string"){
const err10 = {instancePath:instancePath+"/facts/" + i0+"/description",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/properties/description/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
}
else {
const err11 = {instancePath:instancePath+"/facts/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphFact/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
}
else {
const err12 = {instancePath:instancePath+"/facts",schemaPath:"#/properties/facts/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.intents !== undefined){
let data5 = data.intents;
if(Array.isArray(data5)){
const len1 = data5.length;
for(let i1=0; i1<len1; i1++){
let data6 = data5[i1];
if(data6 && typeof data6 == "object" && !Array.isArray(data6)){
if(data6.id === undefined){
const err13 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data6.from === undefined){
const err14 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "from"},message:"must have required property '"+"from"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data6.to === undefined){
const err15 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "to"},message:"must have required property '"+"to"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(data6.description === undefined){
const err16 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "description"},message:"must have required property '"+"description"+"'"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(data6.creator === undefined){
const err17 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "creator"},message:"must have required property '"+"creator"+"'"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data6.worker === undefined){
const err18 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "worker"},message:"must have required property '"+"worker"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data6.last_heartbeat_at === undefined){
const err19 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "last_heartbeat_at"},message:"must have required property '"+"last_heartbeat_at"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data6.created_at === undefined){
const err20 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data6.concluded_at === undefined){
const err21 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/required",keyword:"required",params:{missingProperty: "concluded_at"},message:"must have required property '"+"concluded_at"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
for(const key2 in data6){
if(!(func22.call(schema115.properties, key2))){
const err22 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data6.id !== undefined){
if(typeof data6.id !== "string"){
const err23 = {instancePath:instancePath+"/intents/" + i1+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data6.from !== undefined){
let data8 = data6.from;
if(Array.isArray(data8)){
const len2 = data8.length;
for(let i2=0; i2<len2; i2++){
if(typeof data8[i2] !== "string"){
const err24 = {instancePath:instancePath+"/intents/" + i1+"/from/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/from/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
}
else {
const err25 = {instancePath:instancePath+"/intents/" + i1+"/from",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/from/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data6.to !== undefined){
let data10 = data6.to;
const _errs28 = errors;
let valid11 = false;
const _errs29 = errors;
if(typeof data10 !== "string"){
const err26 = {instancePath:instancePath+"/intents/" + i1+"/to",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/to/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
var _valid0 = _errs29 === errors;
valid11 = valid11 || _valid0;
const _errs31 = errors;
if(data10 !== null){
const err27 = {instancePath:instancePath+"/intents/" + i1+"/to",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/to/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
var _valid0 = _errs31 === errors;
valid11 = valid11 || _valid0;
if(!valid11){
const err28 = {instancePath:instancePath+"/intents/" + i1+"/to",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/to/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
else {
errors = _errs28;
if(vErrors !== null){
if(_errs28){
vErrors.length = _errs28;
}
else {
vErrors = null;
}
}
}
}
if(data6.description !== undefined){
if(typeof data6.description !== "string"){
const err29 = {instancePath:instancePath+"/intents/" + i1+"/description",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/description/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data6.creator !== undefined){
if(typeof data6.creator !== "string"){
const err30 = {instancePath:instancePath+"/intents/" + i1+"/creator",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/creator/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data6.worker !== undefined){
let data13 = data6.worker;
const _errs38 = errors;
let valid12 = false;
const _errs39 = errors;
if(typeof data13 !== "string"){
const err31 = {instancePath:instancePath+"/intents/" + i1+"/worker",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/worker/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
var _valid1 = _errs39 === errors;
valid12 = valid12 || _valid1;
const _errs41 = errors;
if(data13 !== null){
const err32 = {instancePath:instancePath+"/intents/" + i1+"/worker",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/worker/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
var _valid1 = _errs41 === errors;
valid12 = valid12 || _valid1;
if(!valid12){
const err33 = {instancePath:instancePath+"/intents/" + i1+"/worker",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/worker/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
else {
errors = _errs38;
if(vErrors !== null){
if(_errs38){
vErrors.length = _errs38;
}
else {
vErrors = null;
}
}
}
}
if(data6.last_heartbeat_at !== undefined){
let data14 = data6.last_heartbeat_at;
const _errs44 = errors;
let valid13 = false;
const _errs45 = errors;
if(typeof data14 !== "string"){
const err34 = {instancePath:instancePath+"/intents/" + i1+"/last_heartbeat_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/last_heartbeat_at/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid2 = _errs45 === errors;
valid13 = valid13 || _valid2;
const _errs47 = errors;
if(data14 !== null){
const err35 = {instancePath:instancePath+"/intents/" + i1+"/last_heartbeat_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/last_heartbeat_at/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid2 = _errs47 === errors;
valid13 = valid13 || _valid2;
if(!valid13){
const err36 = {instancePath:instancePath+"/intents/" + i1+"/last_heartbeat_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/last_heartbeat_at/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
else {
errors = _errs44;
if(vErrors !== null){
if(_errs44){
vErrors.length = _errs44;
}
else {
vErrors = null;
}
}
}
}
if(data6.created_at !== undefined){
if(typeof data6.created_at !== "string"){
const err37 = {instancePath:instancePath+"/intents/" + i1+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
}
if(data6.concluded_at !== undefined){
let data16 = data6.concluded_at;
const _errs52 = errors;
let valid14 = false;
const _errs53 = errors;
if(typeof data16 !== "string"){
const err38 = {instancePath:instancePath+"/intents/" + i1+"/concluded_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/concluded_at/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid3 = _errs53 === errors;
valid14 = valid14 || _valid3;
const _errs55 = errors;
if(data16 !== null){
const err39 = {instancePath:instancePath+"/intents/" + i1+"/concluded_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/concluded_at/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
var _valid3 = _errs55 === errors;
valid14 = valid14 || _valid3;
if(!valid14){
const err40 = {instancePath:instancePath+"/intents/" + i1+"/concluded_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/properties/concluded_at/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
else {
errors = _errs52;
if(vErrors !== null){
if(_errs52){
vErrors.length = _errs52;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err41 = {instancePath:instancePath+"/intents/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphIntent/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
}
else {
const err42 = {instancePath:instancePath+"/intents",schemaPath:"#/properties/intents/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
if(data.hints !== undefined){
let data17 = data.hints;
if(Array.isArray(data17)){
const len3 = data17.length;
for(let i3=0; i3<len3; i3++){
let data18 = data17[i3];
if(data18 && typeof data18 == "object" && !Array.isArray(data18)){
if(data18.id === undefined){
const err43 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if(data18.content === undefined){
const err44 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/required",keyword:"required",params:{missingProperty: "content"},message:"must have required property '"+"content"+"'"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
if(data18.creator === undefined){
const err45 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/required",keyword:"required",params:{missingProperty: "creator"},message:"must have required property '"+"creator"+"'"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
if(data18.created_at === undefined){
const err46 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
for(const key3 in data18){
if(!((((key3 === "id") || (key3 === "content")) || (key3 === "creator")) || (key3 === "created_at"))){
const err47 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key3},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
if(data18.id !== undefined){
if(typeof data18.id !== "string"){
const err48 = {instancePath:instancePath+"/hints/" + i3+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data18.content !== undefined){
if(typeof data18.content !== "string"){
const err49 = {instancePath:instancePath+"/hints/" + i3+"/content",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/properties/content/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
if(data18.creator !== undefined){
if(typeof data18.creator !== "string"){
const err50 = {instancePath:instancePath+"/hints/" + i3+"/creator",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/properties/creator/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
if(data18.created_at !== undefined){
if(typeof data18.created_at !== "string"){
const err51 = {instancePath:instancePath+"/hints/" + i3+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err52 = {instancePath:instancePath+"/hints/" + i3,schemaPath:"urn:wuji:contracts:0.5#/$defs/GraphHint/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
}
else {
const err53 = {instancePath:instancePath+"/hints",schemaPath:"#/properties/hints/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
}
else {
const err54 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
validate100.errors = vErrors;
return errors === 0;
}
validate100.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate99(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate99.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.state === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.native_project_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "native_project_id"},message:"must have required property '"+"native_project_id"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.graph === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "graph"},message:"must have required property '"+"graph"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.captured_at === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "captured_at"},message:"must have required property '"+"captured_at"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.digest === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "digest"},message:"must have required property '"+"digest"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
for(const key0 in data){
if(!(((((key0 === "state") || (key0 === "native_project_id")) || (key0 === "graph")) || (key0 === "captured_at")) || (key0 === "digest"))){
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
if(data.state !== undefined){
let data0 = data.state;
if(typeof data0 !== "string"){
const err6 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(!((data0 === "pending") || (data0 === "available"))){
const err7 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema112.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data.native_project_id !== undefined){
let data1 = data.native_project_id;
const _errs5 = errors;
let valid1 = false;
const _errs6 = errors;
if(typeof data1 !== "string"){
const err8 = {instancePath:instancePath+"/native_project_id",schemaPath:"#/properties/native_project_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
var _valid0 = _errs6 === errors;
valid1 = valid1 || _valid0;
const _errs8 = errors;
if(data1 !== null){
const err9 = {instancePath:instancePath+"/native_project_id",schemaPath:"#/properties/native_project_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
var _valid0 = _errs8 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err10 = {instancePath:instancePath+"/native_project_id",schemaPath:"#/properties/native_project_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
else {
errors = _errs5;
if(vErrors !== null){
if(_errs5){
vErrors.length = _errs5;
}
else {
vErrors = null;
}
}
}
}
if(data.graph !== undefined){
let data2 = data.graph;
const _errs11 = errors;
let valid2 = false;
const _errs12 = errors;
if(!(validate100(data2, {instancePath:instancePath+"/graph",parentData:data,parentDataProperty:"graph",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate100.errors : vErrors.concat(validate100.errors);
errors = vErrors.length;
}
var _valid1 = _errs12 === errors;
valid2 = valid2 || _valid1;
const _errs13 = errors;
if(data2 !== null){
const err11 = {instancePath:instancePath+"/graph",schemaPath:"#/properties/graph/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
var _valid1 = _errs13 === errors;
valid2 = valid2 || _valid1;
if(!valid2){
const err12 = {instancePath:instancePath+"/graph",schemaPath:"#/properties/graph/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
else {
errors = _errs11;
if(vErrors !== null){
if(_errs11){
vErrors.length = _errs11;
}
else {
vErrors = null;
}
}
}
}
if(data.captured_at !== undefined){
let data3 = data.captured_at;
const _errs16 = errors;
let valid3 = false;
const _errs17 = errors;
if(typeof data3 === "string"){
if(!(formats2.validate(data3))){
const err13 = {instancePath:instancePath+"/captured_at",schemaPath:"#/properties/captured_at/anyOf/0/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
else {
const err14 = {instancePath:instancePath+"/captured_at",schemaPath:"#/properties/captured_at/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
var _valid2 = _errs17 === errors;
valid3 = valid3 || _valid2;
const _errs19 = errors;
if(data3 !== null){
const err15 = {instancePath:instancePath+"/captured_at",schemaPath:"#/properties/captured_at/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
var _valid2 = _errs19 === errors;
valid3 = valid3 || _valid2;
if(!valid3){
const err16 = {instancePath:instancePath+"/captured_at",schemaPath:"#/properties/captured_at/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
else {
errors = _errs16;
if(vErrors !== null){
if(_errs16){
vErrors.length = _errs16;
}
else {
vErrors = null;
}
}
}
}
if(data.digest !== undefined){
let data4 = data.digest;
const _errs22 = errors;
let valid4 = false;
const _errs23 = errors;
if(typeof data4 !== "string"){
const err17 = {instancePath:instancePath+"/digest",schemaPath:"#/properties/digest/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
var _valid3 = _errs23 === errors;
valid4 = valid4 || _valid3;
const _errs25 = errors;
if(data4 !== null){
const err18 = {instancePath:instancePath+"/digest",schemaPath:"#/properties/digest/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
var _valid3 = _errs25 === errors;
valid4 = valid4 || _valid3;
if(!valid4){
const err19 = {instancePath:instancePath+"/digest",schemaPath:"#/properties/digest/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
else {
errors = _errs22;
if(vErrors !== null){
if(_errs22){
vErrors.length = _errs22;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err20 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
validate99.errors = vErrors;
return errors === 0;
}
validate99.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateTaskResult = validate102;
const schema117 = {"additionalProperties":false,"properties":{"state":{"enum":["pending","available"],"title":"State","type":"string"},"goal_status":{"enum":["unknown","met","not_met"],"title":"Goal Status","type":"string"},"summary":{"title":"Summary","type":"string"},"limitations":{"items":{"type":"string"},"title":"Limitations","type":"array"},"artifact_ids":{"items":{"format":"uuid","type":"string"},"title":"Artifact Ids","type":"array"},"model_spend":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Model Spend"},"cost_state":{"title":"Cost State","type":"string"},"assessment":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/AssessmentReference"},{"type":"null"}],"default":null}},"required":["state","goal_status","summary","limitations","artifact_ids","model_spend","cost_state"],"title":"TaskResult","type":"object"};
const schema118 = {"additionalProperties":false,"properties":{"plan_id":{"format":"uuid","title":"Plan Id","type":"string"},"revision":{"minimum":1,"title":"Revision","type":"integer"},"outcome":{"enum":["not_assessed","complete","partial","inconclusive"],"title":"Outcome","type":"string"}},"required":["plan_id","revision","outcome"],"title":"AssessmentReference","type":"object"};

function validate102(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate102.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.state === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.goal_status === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "goal_status"},message:"must have required property '"+"goal_status"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.summary === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "summary"},message:"must have required property '"+"summary"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(data.limitations === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "limitations"},message:"must have required property '"+"limitations"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.artifact_ids === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "artifact_ids"},message:"must have required property '"+"artifact_ids"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.model_spend === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "model_spend"},message:"must have required property '"+"model_spend"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.cost_state === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "cost_state"},message:"must have required property '"+"cost_state"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
for(const key0 in data){
if(!((((((((key0 === "state") || (key0 === "goal_status")) || (key0 === "summary")) || (key0 === "limitations")) || (key0 === "artifact_ids")) || (key0 === "model_spend")) || (key0 === "cost_state")) || (key0 === "assessment"))){
const err7 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
}
if(data.state !== undefined){
let data0 = data.state;
if(typeof data0 !== "string"){
const err8 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(!((data0 === "pending") || (data0 === "available"))){
const err9 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema117.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
}
if(data.goal_status !== undefined){
let data1 = data.goal_status;
if(typeof data1 !== "string"){
const err10 = {instancePath:instancePath+"/goal_status",schemaPath:"#/properties/goal_status/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(!(((data1 === "unknown") || (data1 === "met")) || (data1 === "not_met"))){
const err11 = {instancePath:instancePath+"/goal_status",schemaPath:"#/properties/goal_status/enum",keyword:"enum",params:{allowedValues: schema117.properties.goal_status.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
if(data.summary !== undefined){
if(typeof data.summary !== "string"){
const err12 = {instancePath:instancePath+"/summary",schemaPath:"#/properties/summary/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.limitations !== undefined){
let data3 = data.limitations;
if(Array.isArray(data3)){
const len0 = data3.length;
for(let i0=0; i0<len0; i0++){
if(typeof data3[i0] !== "string"){
const err13 = {instancePath:instancePath+"/limitations/" + i0,schemaPath:"#/properties/limitations/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
}
else {
const err14 = {instancePath:instancePath+"/limitations",schemaPath:"#/properties/limitations/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
}
if(data.artifact_ids !== undefined){
let data5 = data.artifact_ids;
if(Array.isArray(data5)){
const len1 = data5.length;
for(let i1=0; i1<len1; i1++){
let data6 = data5[i1];
if(typeof data6 === "string"){
if(!(formats0.test(data6))){
const err15 = {instancePath:instancePath+"/artifact_ids/" + i1,schemaPath:"#/properties/artifact_ids/items/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
else {
const err16 = {instancePath:instancePath+"/artifact_ids/" + i1,schemaPath:"#/properties/artifact_ids/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
}
else {
const err17 = {instancePath:instancePath+"/artifact_ids",schemaPath:"#/properties/artifact_ids/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.model_spend !== undefined){
let data7 = data.model_spend;
const _errs17 = errors;
let valid5 = false;
const _errs18 = errors;
if(typeof data7 !== "string"){
const err18 = {instancePath:instancePath+"/model_spend",schemaPath:"#/properties/model_spend/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
var _valid0 = _errs18 === errors;
valid5 = valid5 || _valid0;
const _errs20 = errors;
if(data7 !== null){
const err19 = {instancePath:instancePath+"/model_spend",schemaPath:"#/properties/model_spend/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
var _valid0 = _errs20 === errors;
valid5 = valid5 || _valid0;
if(!valid5){
const err20 = {instancePath:instancePath+"/model_spend",schemaPath:"#/properties/model_spend/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
else {
errors = _errs17;
if(vErrors !== null){
if(_errs17){
vErrors.length = _errs17;
}
else {
vErrors = null;
}
}
}
}
if(data.cost_state !== undefined){
if(typeof data.cost_state !== "string"){
const err21 = {instancePath:instancePath+"/cost_state",schemaPath:"#/properties/cost_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data.assessment !== undefined){
let data9 = data.assessment;
const _errs25 = errors;
let valid6 = false;
const _errs26 = errors;
if(data9 && typeof data9 == "object" && !Array.isArray(data9)){
if(data9.plan_id === undefined){
const err22 = {instancePath:instancePath+"/assessment",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/required",keyword:"required",params:{missingProperty: "plan_id"},message:"must have required property '"+"plan_id"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data9.revision === undefined){
const err23 = {instancePath:instancePath+"/assessment",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/required",keyword:"required",params:{missingProperty: "revision"},message:"must have required property '"+"revision"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
if(data9.outcome === undefined){
const err24 = {instancePath:instancePath+"/assessment",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/required",keyword:"required",params:{missingProperty: "outcome"},message:"must have required property '"+"outcome"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
for(const key1 in data9){
if(!(((key1 === "plan_id") || (key1 === "revision")) || (key1 === "outcome"))){
const err25 = {instancePath:instancePath+"/assessment",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data9.plan_id !== undefined){
let data10 = data9.plan_id;
if(typeof data10 === "string"){
if(!(formats0.test(data10))){
const err26 = {instancePath:instancePath+"/assessment/plan_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/plan_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err27 = {instancePath:instancePath+"/assessment/plan_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/plan_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data9.revision !== undefined){
let data11 = data9.revision;
if(!(((typeof data11 == "number") && (!(data11 % 1) && !isNaN(data11))) && (isFinite(data11)))){
const err28 = {instancePath:instancePath+"/assessment/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if((typeof data11 == "number") && (isFinite(data11))){
if(data11 < 1 || isNaN(data11)){
const err29 = {instancePath:instancePath+"/assessment/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
}
if(data9.outcome !== undefined){
let data12 = data9.outcome;
if(typeof data12 !== "string"){
const err30 = {instancePath:instancePath+"/assessment/outcome",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/outcome/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(!((((data12 === "not_assessed") || (data12 === "complete")) || (data12 === "partial")) || (data12 === "inconclusive"))){
const err31 = {instancePath:instancePath+"/assessment/outcome",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/properties/outcome/enum",keyword:"enum",params:{allowedValues: schema118.properties.outcome.enum},message:"must be equal to one of the allowed values"};
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
const err32 = {instancePath:instancePath+"/assessment",schemaPath:"urn:wuji:contracts:0.5#/$defs/AssessmentReference/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
var _valid1 = _errs26 === errors;
valid6 = valid6 || _valid1;
const _errs36 = errors;
if(data9 !== null){
const err33 = {instancePath:instancePath+"/assessment",schemaPath:"#/properties/assessment/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
var _valid1 = _errs36 === errors;
valid6 = valid6 || _valid1;
if(!valid6){
const err34 = {instancePath:instancePath+"/assessment",schemaPath:"#/properties/assessment/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
else {
errors = _errs25;
if(vErrors !== null){
if(_errs25){
vErrors.length = _errs25;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err35 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
validate102.errors = vErrors;
return errors === 0;
}
validate102.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateAssessmentView = validate103;
const schema119 = {"additionalProperties":false,"properties":{"state":{"enum":["not_assessed","available"],"title":"State","type":"string"},"profile_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"title":"Profile Id"},"plan_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Plan Id"},"revision":{"default":0,"minimum":0,"title":"Revision","type":"integer"},"progress_digest":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"title":"Progress Digest"},"outcome":{"default":"not_assessed","enum":["not_assessed","complete","partial","inconclusive"],"title":"Outcome","type":"string"},"discovery_state":{"default":"pending","enum":["pending","complete","incomplete"],"title":"Discovery State","type":"string"},"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/CoverageItem"},"maxItems":11,"title":"Items","type":"array"},"limitations":{"items":{"type":"string"},"maxItems":30,"title":"Limitations","type":"array"}},"required":["state"],"title":"AssessmentView","type":"object"};
const schema120 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"target_url":{"title":"Target Url","type":"string"},"rule_id":{"const":"cors-reflection-v1","default":"cors-reflection-v1","title":"Rule Id","type":"string"},"state":{"enum":["pending","evaluated","blocked","inconclusive","not_run"],"title":"State","type":"string"},"verdict":{"anyOf":[{"enum":["unassessed","confirmed","not_reproduced","inconclusive"],"type":"string"},{"type":"null"}],"default":null,"title":"Verdict"},"verification_run_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Verification Run Id"},"result_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"default":null,"title":"Result Id"},"reason":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null,"title":"Reason"}},"required":["id","target_url","state"],"title":"CoverageItem","type":"object"};

function validate103(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate103.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.state === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema119.properties, key0))){
const err1 = {instancePath,schemaPath:"#/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key0},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
}
if(data.state !== undefined){
let data0 = data.state;
if(typeof data0 !== "string"){
const err2 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
if(!((data0 === "not_assessed") || (data0 === "available"))){
const err3 = {instancePath:instancePath+"/state",schemaPath:"#/properties/state/enum",keyword:"enum",params:{allowedValues: schema119.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
}
if(data.profile_id !== undefined){
let data1 = data.profile_id;
const _errs5 = errors;
let valid1 = false;
const _errs6 = errors;
if(typeof data1 !== "string"){
const err4 = {instancePath:instancePath+"/profile_id",schemaPath:"#/properties/profile_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
var _valid0 = _errs6 === errors;
valid1 = valid1 || _valid0;
const _errs8 = errors;
if(data1 !== null){
const err5 = {instancePath:instancePath+"/profile_id",schemaPath:"#/properties/profile_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
var _valid0 = _errs8 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err6 = {instancePath:instancePath+"/profile_id",schemaPath:"#/properties/profile_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
else {
errors = _errs5;
if(vErrors !== null){
if(_errs5){
vErrors.length = _errs5;
}
else {
vErrors = null;
}
}
}
}
if(data.plan_id !== undefined){
let data2 = data.plan_id;
const _errs11 = errors;
let valid2 = false;
const _errs12 = errors;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err7 = {instancePath:instancePath+"/plan_id",schemaPath:"#/properties/plan_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err8 = {instancePath:instancePath+"/plan_id",schemaPath:"#/properties/plan_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
var _valid1 = _errs12 === errors;
valid2 = valid2 || _valid1;
const _errs14 = errors;
if(data2 !== null){
const err9 = {instancePath:instancePath+"/plan_id",schemaPath:"#/properties/plan_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
var _valid1 = _errs14 === errors;
valid2 = valid2 || _valid1;
if(!valid2){
const err10 = {instancePath:instancePath+"/plan_id",schemaPath:"#/properties/plan_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
else {
errors = _errs11;
if(vErrors !== null){
if(_errs11){
vErrors.length = _errs11;
}
else {
vErrors = null;
}
}
}
}
if(data.revision !== undefined){
let data3 = data.revision;
if(!(((typeof data3 == "number") && (!(data3 % 1) && !isNaN(data3))) && (isFinite(data3)))){
const err11 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if((typeof data3 == "number") && (isFinite(data3))){
if(data3 < 0 || isNaN(data3)){
const err12 = {instancePath:instancePath+"/revision",schemaPath:"#/properties/revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
}
if(data.progress_digest !== undefined){
let data4 = data.progress_digest;
const _errs19 = errors;
let valid3 = false;
const _errs20 = errors;
if(typeof data4 !== "string"){
const err13 = {instancePath:instancePath+"/progress_digest",schemaPath:"#/properties/progress_digest/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
var _valid2 = _errs20 === errors;
valid3 = valid3 || _valid2;
const _errs22 = errors;
if(data4 !== null){
const err14 = {instancePath:instancePath+"/progress_digest",schemaPath:"#/properties/progress_digest/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
var _valid2 = _errs22 === errors;
valid3 = valid3 || _valid2;
if(!valid3){
const err15 = {instancePath:instancePath+"/progress_digest",schemaPath:"#/properties/progress_digest/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
else {
errors = _errs19;
if(vErrors !== null){
if(_errs19){
vErrors.length = _errs19;
}
else {
vErrors = null;
}
}
}
}
if(data.outcome !== undefined){
let data5 = data.outcome;
if(typeof data5 !== "string"){
const err16 = {instancePath:instancePath+"/outcome",schemaPath:"#/properties/outcome/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(!((((data5 === "not_assessed") || (data5 === "complete")) || (data5 === "partial")) || (data5 === "inconclusive"))){
const err17 = {instancePath:instancePath+"/outcome",schemaPath:"#/properties/outcome/enum",keyword:"enum",params:{allowedValues: schema119.properties.outcome.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data.discovery_state !== undefined){
let data6 = data.discovery_state;
if(typeof data6 !== "string"){
const err18 = {instancePath:instancePath+"/discovery_state",schemaPath:"#/properties/discovery_state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(!(((data6 === "pending") || (data6 === "complete")) || (data6 === "incomplete"))){
const err19 = {instancePath:instancePath+"/discovery_state",schemaPath:"#/properties/discovery_state/enum",keyword:"enum",params:{allowedValues: schema119.properties.discovery_state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
if(data.items !== undefined){
let data7 = data.items;
if(Array.isArray(data7)){
if(data7.length > 11){
const err20 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/maxItems",keyword:"maxItems",params:{limit: 11},message:"must NOT have more than 11 items"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
const len0 = data7.length;
for(let i0=0; i0<len0; i0++){
let data8 = data7[i0];
if(data8 && typeof data8 == "object" && !Array.isArray(data8)){
if(data8.id === undefined){
const err21 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data8.target_url === undefined){
const err22 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
if(data8.state === undefined){
const err23 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/required",keyword:"required",params:{missingProperty: "state"},message:"must have required property '"+"state"+"'"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
for(const key1 in data8){
if(!((((((((key1 === "id") || (key1 === "target_url")) || (key1 === "rule_id")) || (key1 === "state")) || (key1 === "verdict")) || (key1 === "verification_run_id")) || (key1 === "result_id")) || (key1 === "reason"))){
const err24 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data8.id !== undefined){
let data9 = data8.id;
if(typeof data9 === "string"){
if(!(formats0.test(data9))){
const err25 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
else {
const err26 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
}
if(data8.target_url !== undefined){
if(typeof data8.target_url !== "string"){
const err27 = {instancePath:instancePath+"/items/" + i0+"/target_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data8.rule_id !== undefined){
let data11 = data8.rule_id;
if(typeof data11 !== "string"){
const err28 = {instancePath:instancePath+"/items/" + i0+"/rule_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/rule_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if("cors-reflection-v1" !== data11){
const err29 = {instancePath:instancePath+"/items/" + i0+"/rule_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/rule_id/const",keyword:"const",params:{allowedValue: "cors-reflection-v1"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data8.state !== undefined){
let data12 = data8.state;
if(typeof data12 !== "string"){
const err30 = {instancePath:instancePath+"/items/" + i0+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/state/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(!(((((data12 === "pending") || (data12 === "evaluated")) || (data12 === "blocked")) || (data12 === "inconclusive")) || (data12 === "not_run"))){
const err31 = {instancePath:instancePath+"/items/" + i0+"/state",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/state/enum",keyword:"enum",params:{allowedValues: schema120.properties.state.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
}
if(data8.verdict !== undefined){
let data13 = data8.verdict;
const _errs43 = errors;
let valid8 = false;
const _errs44 = errors;
if(typeof data13 !== "string"){
const err32 = {instancePath:instancePath+"/items/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verdict/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
if(!((((data13 === "unassessed") || (data13 === "confirmed")) || (data13 === "not_reproduced")) || (data13 === "inconclusive"))){
const err33 = {instancePath:instancePath+"/items/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verdict/anyOf/0/enum",keyword:"enum",params:{allowedValues: schema120.properties.verdict.anyOf[0].enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
var _valid3 = _errs44 === errors;
valid8 = valid8 || _valid3;
const _errs46 = errors;
if(data13 !== null){
const err34 = {instancePath:instancePath+"/items/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verdict/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
var _valid3 = _errs46 === errors;
valid8 = valid8 || _valid3;
if(!valid8){
const err35 = {instancePath:instancePath+"/items/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verdict/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
else {
errors = _errs43;
if(vErrors !== null){
if(_errs43){
vErrors.length = _errs43;
}
else {
vErrors = null;
}
}
}
}
if(data8.verification_run_id !== undefined){
let data14 = data8.verification_run_id;
const _errs49 = errors;
let valid9 = false;
const _errs50 = errors;
if(typeof data14 === "string"){
if(!(formats0.test(data14))){
const err36 = {instancePath:instancePath+"/items/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verification_run_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
else {
const err37 = {instancePath:instancePath+"/items/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verification_run_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
var _valid4 = _errs50 === errors;
valid9 = valid9 || _valid4;
const _errs52 = errors;
if(data14 !== null){
const err38 = {instancePath:instancePath+"/items/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verification_run_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
var _valid4 = _errs52 === errors;
valid9 = valid9 || _valid4;
if(!valid9){
const err39 = {instancePath:instancePath+"/items/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/verification_run_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
else {
errors = _errs49;
if(vErrors !== null){
if(_errs49){
vErrors.length = _errs49;
}
else {
vErrors = null;
}
}
}
}
if(data8.result_id !== undefined){
let data15 = data8.result_id;
const _errs55 = errors;
let valid10 = false;
const _errs56 = errors;
if(typeof data15 === "string"){
if(!(formats0.test(data15))){
const err40 = {instancePath:instancePath+"/items/" + i0+"/result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/result_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
else {
const err41 = {instancePath:instancePath+"/items/" + i0+"/result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/result_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
var _valid5 = _errs56 === errors;
valid10 = valid10 || _valid5;
const _errs58 = errors;
if(data15 !== null){
const err42 = {instancePath:instancePath+"/items/" + i0+"/result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/result_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
var _valid5 = _errs58 === errors;
valid10 = valid10 || _valid5;
if(!valid10){
const err43 = {instancePath:instancePath+"/items/" + i0+"/result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/result_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
else {
errors = _errs55;
if(vErrors !== null){
if(_errs55){
vErrors.length = _errs55;
}
else {
vErrors = null;
}
}
}
}
if(data8.reason !== undefined){
let data16 = data8.reason;
const _errs61 = errors;
let valid11 = false;
const _errs62 = errors;
if(typeof data16 !== "string"){
const err44 = {instancePath:instancePath+"/items/" + i0+"/reason",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/reason/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
var _valid6 = _errs62 === errors;
valid11 = valid11 || _valid6;
const _errs64 = errors;
if(data16 !== null){
const err45 = {instancePath:instancePath+"/items/" + i0+"/reason",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/reason/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
var _valid6 = _errs64 === errors;
valid11 = valid11 || _valid6;
if(!valid11){
const err46 = {instancePath:instancePath+"/items/" + i0+"/reason",schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/properties/reason/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
else {
errors = _errs61;
if(vErrors !== null){
if(_errs61){
vErrors.length = _errs61;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err47 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/CoverageItem/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
}
else {
const err48 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data.limitations !== undefined){
let data17 = data.limitations;
if(Array.isArray(data17)){
if(data17.length > 30){
const err49 = {instancePath:instancePath+"/limitations",schemaPath:"#/properties/limitations/maxItems",keyword:"maxItems",params:{limit: 30},message:"must NOT have more than 30 items"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
const len1 = data17.length;
for(let i1=0; i1<len1; i1++){
if(typeof data17[i1] !== "string"){
const err50 = {instancePath:instancePath+"/limitations/" + i1,schemaPath:"#/properties/limitations/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
}
else {
const err51 = {instancePath:instancePath+"/limitations",schemaPath:"#/properties/limitations/type",keyword:"type",params:{type: "array"},message:"must be array"};
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
else {
const err52 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
validate103.errors = vErrors;
return errors === 0;
}
validate103.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateObservationPage = validate104;
const schema121 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/Observation"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"ObservationPage","type":"object"};
const schema122 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"tool_call_id":{"format":"uuid","title":"Tool Call Id","type":"string"},"agent_run_id":{"format":"uuid","title":"Agent Run Id","type":"string"},"target_url":{"title":"Target Url","type":"string"},"method":{"enum":["GET","HEAD","OPTIONS"],"title":"Method","type":"string"},"request_headers":{"additionalProperties":{"type":"string"},"title":"Request Headers","type":"object"},"response_status":{"anyOf":[{"type":"integer"},{"type":"null"}],"title":"Response Status"},"response_headers":{"additionalProperties":{"type":"string"},"title":"Response Headers","type":"object"},"complete":{"title":"Complete","type":"boolean"},"termination":{"enum":["complete","size_limit","timeout","cancelled","network_error"],"title":"Termination","type":"string"},"body_bytes":{"maximum":1048576,"minimum":0,"title":"Body Bytes","type":"integer"},"body_sha256":{"title":"Body Sha256","type":"string"},"body_encoding":{"const":"client-decoded","title":"Body Encoding","type":"string"},"redacted_headers":{"items":{"type":"string"},"title":"Redacted Headers","type":"array"},"artifact_id":{"format":"uuid","title":"Artifact Id","type":"string"},"body_artifact_id":{"format":"uuid","title":"Body Artifact Id","type":"string"},"started_at":{"format":"date-time","title":"Started At","type":"string"},"finished_at":{"format":"date-time","title":"Finished At","type":"string"},"created_at":{"format":"date-time","title":"Created At","type":"string"}},"required":["id","tool_call_id","agent_run_id","target_url","method","request_headers","response_status","response_headers","complete","termination","body_bytes","body_sha256","body_encoding","redacted_headers","artifact_id","body_artifact_id","started_at","finished_at","created_at"],"title":"Observation","type":"object"};

function validate104(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate104.evaluated;
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
let data1 = data0[i0];
if(data1 && typeof data1 == "object" && !Array.isArray(data1)){
if(data1.id === undefined){
const err4 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data1.tool_call_id === undefined){
const err5 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "tool_call_id"},message:"must have required property '"+"tool_call_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data1.agent_run_id === undefined){
const err6 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "agent_run_id"},message:"must have required property '"+"agent_run_id"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data1.target_url === undefined){
const err7 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "target_url"},message:"must have required property '"+"target_url"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data1.method === undefined){
const err8 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "method"},message:"must have required property '"+"method"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data1.request_headers === undefined){
const err9 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "request_headers"},message:"must have required property '"+"request_headers"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data1.response_status === undefined){
const err10 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "response_status"},message:"must have required property '"+"response_status"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data1.response_headers === undefined){
const err11 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "response_headers"},message:"must have required property '"+"response_headers"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data1.complete === undefined){
const err12 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "complete"},message:"must have required property '"+"complete"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
if(data1.termination === undefined){
const err13 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "termination"},message:"must have required property '"+"termination"+"'"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
if(data1.body_bytes === undefined){
const err14 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "body_bytes"},message:"must have required property '"+"body_bytes"+"'"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if(data1.body_sha256 === undefined){
const err15 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "body_sha256"},message:"must have required property '"+"body_sha256"+"'"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
if(data1.body_encoding === undefined){
const err16 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "body_encoding"},message:"must have required property '"+"body_encoding"+"'"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
if(data1.redacted_headers === undefined){
const err17 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "redacted_headers"},message:"must have required property '"+"redacted_headers"+"'"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
if(data1.artifact_id === undefined){
const err18 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "artifact_id"},message:"must have required property '"+"artifact_id"+"'"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if(data1.body_artifact_id === undefined){
const err19 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "body_artifact_id"},message:"must have required property '"+"body_artifact_id"+"'"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
if(data1.started_at === undefined){
const err20 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "started_at"},message:"must have required property '"+"started_at"+"'"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(data1.finished_at === undefined){
const err21 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "finished_at"},message:"must have required property '"+"finished_at"+"'"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
if(data1.created_at === undefined){
const err22 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
for(const key1 in data1){
if(!(func22.call(schema122.properties, key1))){
const err23 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data1.id !== undefined){
let data2 = data1.id;
if(typeof data2 === "string"){
if(!(formats0.test(data2))){
const err24 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err25 = {instancePath:instancePath+"/items/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
if(data1.tool_call_id !== undefined){
let data3 = data1.tool_call_id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err26 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/tool_call_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err27 = {instancePath:instancePath+"/items/" + i0+"/tool_call_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/tool_call_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
}
if(data1.agent_run_id !== undefined){
let data4 = data1.agent_run_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err28 = {instancePath:instancePath+"/items/" + i0+"/agent_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/agent_run_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
}
else {
const err29 = {instancePath:instancePath+"/items/" + i0+"/agent_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/agent_run_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
}
if(data1.target_url !== undefined){
if(typeof data1.target_url !== "string"){
const err30 = {instancePath:instancePath+"/items/" + i0+"/target_url",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/target_url/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
if(data1.method !== undefined){
let data6 = data1.method;
if(typeof data6 !== "string"){
const err31 = {instancePath:instancePath+"/items/" + i0+"/method",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/method/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
if(!(((data6 === "GET") || (data6 === "HEAD")) || (data6 === "OPTIONS"))){
const err32 = {instancePath:instancePath+"/items/" + i0+"/method",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/method/enum",keyword:"enum",params:{allowedValues: schema122.properties.method.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data1.request_headers !== undefined){
let data7 = data1.request_headers;
if(data7 && typeof data7 == "object" && !Array.isArray(data7)){
for(const key2 in data7){
if(typeof data7[key2] !== "string"){
const err33 = {instancePath:instancePath+"/items/" + i0+"/request_headers/" + key2.replace(/~/g, "~0").replace(/\//g, "~1"),schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/request_headers/additionalProperties/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err34 = {instancePath:instancePath+"/items/" + i0+"/request_headers",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/request_headers/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
if(data1.response_status !== undefined){
let data9 = data1.response_status;
const _errs24 = errors;
let valid6 = false;
const _errs25 = errors;
if(!(((typeof data9 == "number") && (!(data9 % 1) && !isNaN(data9))) && (isFinite(data9)))){
const err35 = {instancePath:instancePath+"/items/" + i0+"/response_status",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/response_status/anyOf/0/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
var _valid0 = _errs25 === errors;
valid6 = valid6 || _valid0;
const _errs27 = errors;
if(data9 !== null){
const err36 = {instancePath:instancePath+"/items/" + i0+"/response_status",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/response_status/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
var _valid0 = _errs27 === errors;
valid6 = valid6 || _valid0;
if(!valid6){
const err37 = {instancePath:instancePath+"/items/" + i0+"/response_status",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/response_status/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
else {
errors = _errs24;
if(vErrors !== null){
if(_errs24){
vErrors.length = _errs24;
}
else {
vErrors = null;
}
}
}
}
if(data1.response_headers !== undefined){
let data10 = data1.response_headers;
if(data10 && typeof data10 == "object" && !Array.isArray(data10)){
for(const key3 in data10){
if(typeof data10[key3] !== "string"){
const err38 = {instancePath:instancePath+"/items/" + i0+"/response_headers/" + key3.replace(/~/g, "~0").replace(/\//g, "~1"),schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/response_headers/additionalProperties/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
}
else {
const err39 = {instancePath:instancePath+"/items/" + i0+"/response_headers",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/response_headers/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
}
if(data1.complete !== undefined){
if(typeof data1.complete !== "boolean"){
const err40 = {instancePath:instancePath+"/items/" + i0+"/complete",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/complete/type",keyword:"type",params:{type: "boolean"},message:"must be boolean"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
if(data1.termination !== undefined){
let data13 = data1.termination;
if(typeof data13 !== "string"){
const err41 = {instancePath:instancePath+"/items/" + i0+"/termination",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/termination/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
if(!(((((data13 === "complete") || (data13 === "size_limit")) || (data13 === "timeout")) || (data13 === "cancelled")) || (data13 === "network_error"))){
const err42 = {instancePath:instancePath+"/items/" + i0+"/termination",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/termination/enum",keyword:"enum",params:{allowedValues: schema122.properties.termination.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
if(data1.body_bytes !== undefined){
let data14 = data1.body_bytes;
if(!(((typeof data14 == "number") && (!(data14 % 1) && !isNaN(data14))) && (isFinite(data14)))){
const err43 = {instancePath:instancePath+"/items/" + i0+"/body_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_bytes/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
if((typeof data14 == "number") && (isFinite(data14))){
if(data14 > 1048576 || isNaN(data14)){
const err44 = {instancePath:instancePath+"/items/" + i0+"/body_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_bytes/maximum",keyword:"maximum",params:{comparison: "<=", limit: 1048576},message:"must be <= 1048576"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
if(data14 < 0 || isNaN(data14)){
const err45 = {instancePath:instancePath+"/items/" + i0+"/body_bytes",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_bytes/minimum",keyword:"minimum",params:{comparison: ">=", limit: 0},message:"must be >= 0"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
}
if(data1.body_sha256 !== undefined){
if(typeof data1.body_sha256 !== "string"){
const err46 = {instancePath:instancePath+"/items/" + i0+"/body_sha256",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_sha256/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data1.body_encoding !== undefined){
let data16 = data1.body_encoding;
if(typeof data16 !== "string"){
const err47 = {instancePath:instancePath+"/items/" + i0+"/body_encoding",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_encoding/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
if("client-decoded" !== data16){
const err48 = {instancePath:instancePath+"/items/" + i0+"/body_encoding",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_encoding/const",keyword:"const",params:{allowedValue: "client-decoded"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data1.redacted_headers !== undefined){
let data17 = data1.redacted_headers;
if(Array.isArray(data17)){
const len1 = data17.length;
for(let i1=0; i1<len1; i1++){
if(typeof data17[i1] !== "string"){
const err49 = {instancePath:instancePath+"/items/" + i0+"/redacted_headers/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/redacted_headers/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
}
else {
const err50 = {instancePath:instancePath+"/items/" + i0+"/redacted_headers",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/redacted_headers/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
if(data1.artifact_id !== undefined){
let data19 = data1.artifact_id;
if(typeof data19 === "string"){
if(!(formats0.test(data19))){
const err51 = {instancePath:instancePath+"/items/" + i0+"/artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/artifact_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
}
else {
const err52 = {instancePath:instancePath+"/items/" + i0+"/artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/artifact_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
if(data1.body_artifact_id !== undefined){
let data20 = data1.body_artifact_id;
if(typeof data20 === "string"){
if(!(formats0.test(data20))){
const err53 = {instancePath:instancePath+"/items/" + i0+"/body_artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_artifact_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
else {
const err54 = {instancePath:instancePath+"/items/" + i0+"/body_artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/body_artifact_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
}
if(data1.started_at !== undefined){
let data21 = data1.started_at;
if(typeof data21 === "string"){
if(!(formats2.validate(data21))){
const err55 = {instancePath:instancePath+"/items/" + i0+"/started_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/started_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err55];
}
else {
vErrors.push(err55);
}
errors++;
}
}
else {
const err56 = {instancePath:instancePath+"/items/" + i0+"/started_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/started_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err56];
}
else {
vErrors.push(err56);
}
errors++;
}
}
if(data1.finished_at !== undefined){
let data22 = data1.finished_at;
if(typeof data22 === "string"){
if(!(formats2.validate(data22))){
const err57 = {instancePath:instancePath+"/items/" + i0+"/finished_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/finished_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err57];
}
else {
vErrors.push(err57);
}
errors++;
}
}
else {
const err58 = {instancePath:instancePath+"/items/" + i0+"/finished_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/finished_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err58];
}
else {
vErrors.push(err58);
}
errors++;
}
}
if(data1.created_at !== undefined){
let data23 = data1.created_at;
if(typeof data23 === "string"){
if(!(formats2.validate(data23))){
const err59 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err59];
}
else {
vErrors.push(err59);
}
errors++;
}
}
else {
const err60 = {instancePath:instancePath+"/items/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err60];
}
else {
vErrors.push(err60);
}
errors++;
}
}
}
else {
const err61 = {instancePath:instancePath+"/items/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/Observation/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err61];
}
else {
vErrors.push(err61);
}
errors++;
}
}
}
else {
const err62 = {instancePath:instancePath+"/items",schemaPath:"#/properties/items/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err62];
}
else {
vErrors.push(err62);
}
errors++;
}
}
if(data.next_cursor !== undefined){
let data24 = data.next_cursor;
const _errs59 = errors;
let valid10 = false;
const _errs60 = errors;
if(typeof data24 !== "string"){
const err63 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err63];
}
else {
vErrors.push(err63);
}
errors++;
}
var _valid1 = _errs60 === errors;
valid10 = valid10 || _valid1;
const _errs62 = errors;
if(data24 !== null){
const err64 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err64];
}
else {
vErrors.push(err64);
}
errors++;
}
var _valid1 = _errs62 === errors;
valid10 = valid10 || _valid1;
if(!valid10){
const err65 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err65];
}
else {
vErrors.push(err65);
}
errors++;
}
else {
errors = _errs59;
if(vErrors !== null){
if(_errs59){
vErrors.length = _errs59;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err66 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err66];
}
else {
vErrors.push(err66);
}
errors++;
}
validate104.errors = vErrors;
return errors === 0;
}
validate104.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateVerificationPage = validate105;
const schema123 = {"additionalProperties":false,"properties":{"items":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/VerificationRun"},"maxItems":100,"title":"Items","type":"array"},"next_cursor":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Next Cursor"}},"required":["items","next_cursor"],"title":"VerificationPage","type":"object"};
const schema124 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"coverage_item_id":{"format":"uuid","title":"Coverage Item Id","type":"string"},"target_url":{"title":"Target Url","type":"string"},"rule_id":{"const":"cors-reflection-v1","title":"Rule Id","type":"string"},"claim":{"title":"Claim","type":"string"},"agent_run_id":{"format":"uuid","title":"Agent Run Id","type":"string"},"intent_id":{"anyOf":[{"type":"string"},{"type":"null"}],"title":"Intent Id"},"created_at":{"format":"date-time","title":"Created At","type":"string"},"latest_result":{"anyOf":[{"$ref":"urn:wuji:contracts:0.5#/$defs/VerificationResult"},{"type":"null"}],"default":null}},"required":["id","coverage_item_id","target_url","rule_id","claim","agent_run_id","intent_id","created_at"],"title":"VerificationRun","type":"object"};
const schema125 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"verification_run_id":{"format":"uuid","title":"Verification Run Id","type":"string"},"revision":{"minimum":1,"title":"Revision","type":"integer"},"verdict":{"enum":["unassessed","confirmed","not_reproduced","inconclusive"],"title":"Verdict","type":"string"},"reason":{"title":"Reason","type":"string"},"limitations":{"items":{"type":"string"},"title":"Limitations","type":"array"},"supersedes_result_id":{"anyOf":[{"format":"uuid","type":"string"},{"type":"null"}],"title":"Supersedes Result Id"},"created_at":{"format":"date-time","title":"Created At","type":"string"}},"required":["id","verification_run_id","revision","verdict","reason","limitations","supersedes_result_id","created_at"],"title":"VerificationResult","type":"object"};

function validate106(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate106.evaluated;
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
if(data.coverage_item_id === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "coverage_item_id"},message:"must have required property '"+"coverage_item_id"+"'"};
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
if(data.rule_id === undefined){
const err3 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "rule_id"},message:"must have required property '"+"rule_id"+"'"};
if(vErrors === null){
vErrors = [err3];
}
else {
vErrors.push(err3);
}
errors++;
}
if(data.claim === undefined){
const err4 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "claim"},message:"must have required property '"+"claim"+"'"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
if(data.agent_run_id === undefined){
const err5 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "agent_run_id"},message:"must have required property '"+"agent_run_id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data.intent_id === undefined){
const err6 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "intent_id"},message:"must have required property '"+"intent_id"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data.created_at === undefined){
const err7 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
for(const key0 in data){
if(!(func22.call(schema124.properties, key0))){
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
if(data.id !== undefined){
let data0 = data.id;
if(typeof data0 === "string"){
if(!(formats0.test(data0))){
const err9 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err10 = {instancePath:instancePath+"/id",schemaPath:"#/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
}
if(data.coverage_item_id !== undefined){
let data1 = data.coverage_item_id;
if(typeof data1 === "string"){
if(!(formats0.test(data1))){
const err11 = {instancePath:instancePath+"/coverage_item_id",schemaPath:"#/properties/coverage_item_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
}
else {
const err12 = {instancePath:instancePath+"/coverage_item_id",schemaPath:"#/properties/coverage_item_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
}
if(data.target_url !== undefined){
if(typeof data.target_url !== "string"){
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
if(data.rule_id !== undefined){
let data3 = data.rule_id;
if(typeof data3 !== "string"){
const err14 = {instancePath:instancePath+"/rule_id",schemaPath:"#/properties/rule_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err14];
}
else {
vErrors.push(err14);
}
errors++;
}
if("cors-reflection-v1" !== data3){
const err15 = {instancePath:instancePath+"/rule_id",schemaPath:"#/properties/rule_id/const",keyword:"const",params:{allowedValue: "cors-reflection-v1"},message:"must be equal to constant"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data.claim !== undefined){
if(typeof data.claim !== "string"){
const err16 = {instancePath:instancePath+"/claim",schemaPath:"#/properties/claim/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err16];
}
else {
vErrors.push(err16);
}
errors++;
}
}
if(data.agent_run_id !== undefined){
let data5 = data.agent_run_id;
if(typeof data5 === "string"){
if(!(formats0.test(data5))){
const err17 = {instancePath:instancePath+"/agent_run_id",schemaPath:"#/properties/agent_run_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
else {
const err18 = {instancePath:instancePath+"/agent_run_id",schemaPath:"#/properties/agent_run_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
}
if(data.intent_id !== undefined){
let data6 = data.intent_id;
const _errs15 = errors;
let valid1 = false;
const _errs16 = errors;
if(typeof data6 !== "string"){
const err19 = {instancePath:instancePath+"/intent_id",schemaPath:"#/properties/intent_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
var _valid0 = _errs16 === errors;
valid1 = valid1 || _valid0;
const _errs18 = errors;
if(data6 !== null){
const err20 = {instancePath:instancePath+"/intent_id",schemaPath:"#/properties/intent_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
var _valid0 = _errs18 === errors;
valid1 = valid1 || _valid0;
if(!valid1){
const err21 = {instancePath:instancePath+"/intent_id",schemaPath:"#/properties/intent_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
else {
errors = _errs15;
if(vErrors !== null){
if(_errs15){
vErrors.length = _errs15;
}
else {
vErrors = null;
}
}
}
}
if(data.created_at !== undefined){
let data7 = data.created_at;
if(typeof data7 === "string"){
if(!(formats2.validate(data7))){
const err22 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
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
const err23 = {instancePath:instancePath+"/created_at",schemaPath:"#/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
if(data.latest_result !== undefined){
let data8 = data.latest_result;
const _errs23 = errors;
let valid2 = false;
const _errs24 = errors;
if(data8 && typeof data8 == "object" && !Array.isArray(data8)){
if(data8.id === undefined){
const err24 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
if(data8.verification_run_id === undefined){
const err25 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "verification_run_id"},message:"must have required property '"+"verification_run_id"+"'"};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
if(data8.revision === undefined){
const err26 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "revision"},message:"must have required property '"+"revision"+"'"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
if(data8.verdict === undefined){
const err27 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "verdict"},message:"must have required property '"+"verdict"+"'"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
if(data8.reason === undefined){
const err28 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "reason"},message:"must have required property '"+"reason"+"'"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
if(data8.limitations === undefined){
const err29 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "limitations"},message:"must have required property '"+"limitations"+"'"};
if(vErrors === null){
vErrors = [err29];
}
else {
vErrors.push(err29);
}
errors++;
}
if(data8.supersedes_result_id === undefined){
const err30 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "supersedes_result_id"},message:"must have required property '"+"supersedes_result_id"+"'"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
if(data8.created_at === undefined){
const err31 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err31];
}
else {
vErrors.push(err31);
}
errors++;
}
for(const key1 in data8){
if(!((((((((key1 === "id") || (key1 === "verification_run_id")) || (key1 === "revision")) || (key1 === "verdict")) || (key1 === "reason")) || (key1 === "limitations")) || (key1 === "supersedes_result_id")) || (key1 === "created_at"))){
const err32 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data8.id !== undefined){
let data9 = data8.id;
if(typeof data9 === "string"){
if(!(formats0.test(data9))){
const err33 = {instancePath:instancePath+"/latest_result/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
}
else {
const err34 = {instancePath:instancePath+"/latest_result/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
}
if(data8.verification_run_id !== undefined){
let data10 = data8.verification_run_id;
if(typeof data10 === "string"){
if(!(formats0.test(data10))){
const err35 = {instancePath:instancePath+"/latest_result/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verification_run_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
}
else {
const err36 = {instancePath:instancePath+"/latest_result/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verification_run_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
}
if(data8.revision !== undefined){
let data11 = data8.revision;
if(!(((typeof data11 == "number") && (!(data11 % 1) && !isNaN(data11))) && (isFinite(data11)))){
const err37 = {instancePath:instancePath+"/latest_result/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if((typeof data11 == "number") && (isFinite(data11))){
if(data11 < 1 || isNaN(data11)){
const err38 = {instancePath:instancePath+"/latest_result/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
}
}
if(data8.verdict !== undefined){
let data12 = data8.verdict;
if(typeof data12 !== "string"){
const err39 = {instancePath:instancePath+"/latest_result/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verdict/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
if(!((((data12 === "unassessed") || (data12 === "confirmed")) || (data12 === "not_reproduced")) || (data12 === "inconclusive"))){
const err40 = {instancePath:instancePath+"/latest_result/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verdict/enum",keyword:"enum",params:{allowedValues: schema125.properties.verdict.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
if(data8.reason !== undefined){
if(typeof data8.reason !== "string"){
const err41 = {instancePath:instancePath+"/latest_result/reason",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/reason/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
if(data8.limitations !== undefined){
let data14 = data8.limitations;
if(Array.isArray(data14)){
const len0 = data14.length;
for(let i0=0; i0<len0; i0++){
if(typeof data14[i0] !== "string"){
const err42 = {instancePath:instancePath+"/latest_result/limitations/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/limitations/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
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
else {
const err43 = {instancePath:instancePath+"/latest_result/limitations",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/limitations/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
if(data8.supersedes_result_id !== undefined){
let data16 = data8.supersedes_result_id;
const _errs43 = errors;
let valid7 = false;
const _errs44 = errors;
if(typeof data16 === "string"){
if(!(formats0.test(data16))){
const err44 = {instancePath:instancePath+"/latest_result/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err45 = {instancePath:instancePath+"/latest_result/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
var _valid2 = _errs44 === errors;
valid7 = valid7 || _valid2;
const _errs46 = errors;
if(data16 !== null){
const err46 = {instancePath:instancePath+"/latest_result/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
var _valid2 = _errs46 === errors;
valid7 = valid7 || _valid2;
if(!valid7){
const err47 = {instancePath:instancePath+"/latest_result/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
else {
errors = _errs43;
if(vErrors !== null){
if(_errs43){
vErrors.length = _errs43;
}
else {
vErrors = null;
}
}
}
}
if(data8.created_at !== undefined){
let data17 = data8.created_at;
if(typeof data17 === "string"){
if(!(formats2.validate(data17))){
const err48 = {instancePath:instancePath+"/latest_result/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
else {
const err49 = {instancePath:instancePath+"/latest_result/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
}
}
else {
const err50 = {instancePath:instancePath+"/latest_result",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
var _valid1 = _errs24 === errors;
valid2 = valid2 || _valid1;
const _errs50 = errors;
if(data8 !== null){
const err51 = {instancePath:instancePath+"/latest_result",schemaPath:"#/properties/latest_result/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err51];
}
else {
vErrors.push(err51);
}
errors++;
}
var _valid1 = _errs50 === errors;
valid2 = valid2 || _valid1;
if(!valid2){
const err52 = {instancePath:instancePath+"/latest_result",schemaPath:"#/properties/latest_result/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
else {
errors = _errs23;
if(vErrors !== null){
if(_errs23){
vErrors.length = _errs23;
}
else {
vErrors = null;
}
}
}
}
}
else {
const err53 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
validate106.errors = vErrors;
return errors === 0;
}
validate106.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};


function validate105(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate105.evaluated;
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
if(!(validate106(data0[i0], {instancePath:instancePath+"/items/" + i0,parentData:data0,parentDataProperty:i0,rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate106.errors : vErrors.concat(validate106.errors);
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
const _errs6 = errors;
let valid3 = false;
const _errs7 = errors;
if(typeof data2 !== "string"){
const err5 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
var _valid0 = _errs7 === errors;
valid3 = valid3 || _valid0;
const _errs9 = errors;
if(data2 !== null){
const err6 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
var _valid0 = _errs9 === errors;
valid3 = valid3 || _valid0;
if(!valid3){
const err7 = {instancePath:instancePath+"/next_cursor",schemaPath:"#/properties/next_cursor/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
else {
errors = _errs6;
if(vErrors !== null){
if(_errs6){
vErrors.length = _errs6;
}
else {
vErrors = null;
}
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
validate105.errors = vErrors;
return errors === 0;
}
validate105.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateVerificationDetail = validate108;
const schema126 = {"additionalProperties":false,"properties":{"verification":{"$ref":"urn:wuji:contracts:0.5#/$defs/VerificationRun"},"results":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/VerificationResult"},"maxItems":100,"title":"Results","type":"array"},"evidence":{"items":{"$ref":"urn:wuji:contracts:0.5#/$defs/EvidenceLink"},"maxItems":200,"title":"Evidence","type":"array"}},"required":["verification","results","evidence"],"title":"VerificationDetail","type":"object"};
const schema128 = {"additionalProperties":false,"properties":{"id":{"format":"uuid","title":"Id","type":"string"},"verification_result_id":{"format":"uuid","title":"Verification Result Id","type":"string"},"observation_id":{"format":"uuid","title":"Observation Id","type":"string"},"artifact_id":{"format":"uuid","title":"Artifact Id","type":"string"},"relation":{"enum":["supports","refutes","limits"],"title":"Relation","type":"string"},"selector":{"additionalProperties":true,"title":"Selector","type":"object"}},"required":["id","verification_result_id","observation_id","artifact_id","relation","selector"],"title":"EvidenceLink","type":"object"};

function validate108(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate108.evaluated;
if(evaluated0.dynamicProps){
evaluated0.props = undefined;
}
if(evaluated0.dynamicItems){
evaluated0.items = undefined;
}
if(data && typeof data == "object" && !Array.isArray(data)){
if(data.verification === undefined){
const err0 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "verification"},message:"must have required property '"+"verification"+"'"};
if(vErrors === null){
vErrors = [err0];
}
else {
vErrors.push(err0);
}
errors++;
}
if(data.results === undefined){
const err1 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "results"},message:"must have required property '"+"results"+"'"};
if(vErrors === null){
vErrors = [err1];
}
else {
vErrors.push(err1);
}
errors++;
}
if(data.evidence === undefined){
const err2 = {instancePath,schemaPath:"#/required",keyword:"required",params:{missingProperty: "evidence"},message:"must have required property '"+"evidence"+"'"};
if(vErrors === null){
vErrors = [err2];
}
else {
vErrors.push(err2);
}
errors++;
}
for(const key0 in data){
if(!(((key0 === "verification") || (key0 === "results")) || (key0 === "evidence"))){
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
if(data.verification !== undefined){
if(!(validate106(data.verification, {instancePath:instancePath+"/verification",parentData:data,parentDataProperty:"verification",rootData,dynamicAnchors}))){
vErrors = vErrors === null ? validate106.errors : vErrors.concat(validate106.errors);
errors = vErrors.length;
}
}
if(data.results !== undefined){
let data1 = data.results;
if(Array.isArray(data1)){
if(data1.length > 100){
const err4 = {instancePath:instancePath+"/results",schemaPath:"#/properties/results/maxItems",keyword:"maxItems",params:{limit: 100},message:"must NOT have more than 100 items"};
if(vErrors === null){
vErrors = [err4];
}
else {
vErrors.push(err4);
}
errors++;
}
const len0 = data1.length;
for(let i0=0; i0<len0; i0++){
let data2 = data1[i0];
if(data2 && typeof data2 == "object" && !Array.isArray(data2)){
if(data2.id === undefined){
const err5 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err5];
}
else {
vErrors.push(err5);
}
errors++;
}
if(data2.verification_run_id === undefined){
const err6 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "verification_run_id"},message:"must have required property '"+"verification_run_id"+"'"};
if(vErrors === null){
vErrors = [err6];
}
else {
vErrors.push(err6);
}
errors++;
}
if(data2.revision === undefined){
const err7 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "revision"},message:"must have required property '"+"revision"+"'"};
if(vErrors === null){
vErrors = [err7];
}
else {
vErrors.push(err7);
}
errors++;
}
if(data2.verdict === undefined){
const err8 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "verdict"},message:"must have required property '"+"verdict"+"'"};
if(vErrors === null){
vErrors = [err8];
}
else {
vErrors.push(err8);
}
errors++;
}
if(data2.reason === undefined){
const err9 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "reason"},message:"must have required property '"+"reason"+"'"};
if(vErrors === null){
vErrors = [err9];
}
else {
vErrors.push(err9);
}
errors++;
}
if(data2.limitations === undefined){
const err10 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "limitations"},message:"must have required property '"+"limitations"+"'"};
if(vErrors === null){
vErrors = [err10];
}
else {
vErrors.push(err10);
}
errors++;
}
if(data2.supersedes_result_id === undefined){
const err11 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "supersedes_result_id"},message:"must have required property '"+"supersedes_result_id"+"'"};
if(vErrors === null){
vErrors = [err11];
}
else {
vErrors.push(err11);
}
errors++;
}
if(data2.created_at === undefined){
const err12 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/required",keyword:"required",params:{missingProperty: "created_at"},message:"must have required property '"+"created_at"+"'"};
if(vErrors === null){
vErrors = [err12];
}
else {
vErrors.push(err12);
}
errors++;
}
for(const key1 in data2){
if(!((((((((key1 === "id") || (key1 === "verification_run_id")) || (key1 === "revision")) || (key1 === "verdict")) || (key1 === "reason")) || (key1 === "limitations")) || (key1 === "supersedes_result_id")) || (key1 === "created_at"))){
const err13 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key1},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err13];
}
else {
vErrors.push(err13);
}
errors++;
}
}
if(data2.id !== undefined){
let data3 = data2.id;
if(typeof data3 === "string"){
if(!(formats0.test(data3))){
const err14 = {instancePath:instancePath+"/results/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err15 = {instancePath:instancePath+"/results/" + i0+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err15];
}
else {
vErrors.push(err15);
}
errors++;
}
}
if(data2.verification_run_id !== undefined){
let data4 = data2.verification_run_id;
if(typeof data4 === "string"){
if(!(formats0.test(data4))){
const err16 = {instancePath:instancePath+"/results/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verification_run_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
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
const err17 = {instancePath:instancePath+"/results/" + i0+"/verification_run_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verification_run_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err17];
}
else {
vErrors.push(err17);
}
errors++;
}
}
if(data2.revision !== undefined){
let data5 = data2.revision;
if(!(((typeof data5 == "number") && (!(data5 % 1) && !isNaN(data5))) && (isFinite(data5)))){
const err18 = {instancePath:instancePath+"/results/" + i0+"/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/revision/type",keyword:"type",params:{type: "integer"},message:"must be integer"};
if(vErrors === null){
vErrors = [err18];
}
else {
vErrors.push(err18);
}
errors++;
}
if((typeof data5 == "number") && (isFinite(data5))){
if(data5 < 1 || isNaN(data5)){
const err19 = {instancePath:instancePath+"/results/" + i0+"/revision",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/revision/minimum",keyword:"minimum",params:{comparison: ">=", limit: 1},message:"must be >= 1"};
if(vErrors === null){
vErrors = [err19];
}
else {
vErrors.push(err19);
}
errors++;
}
}
}
if(data2.verdict !== undefined){
let data6 = data2.verdict;
if(typeof data6 !== "string"){
const err20 = {instancePath:instancePath+"/results/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verdict/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err20];
}
else {
vErrors.push(err20);
}
errors++;
}
if(!((((data6 === "unassessed") || (data6 === "confirmed")) || (data6 === "not_reproduced")) || (data6 === "inconclusive"))){
const err21 = {instancePath:instancePath+"/results/" + i0+"/verdict",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/verdict/enum",keyword:"enum",params:{allowedValues: schema125.properties.verdict.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err21];
}
else {
vErrors.push(err21);
}
errors++;
}
}
if(data2.reason !== undefined){
if(typeof data2.reason !== "string"){
const err22 = {instancePath:instancePath+"/results/" + i0+"/reason",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/reason/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err22];
}
else {
vErrors.push(err22);
}
errors++;
}
}
if(data2.limitations !== undefined){
let data8 = data2.limitations;
if(Array.isArray(data8)){
const len1 = data8.length;
for(let i1=0; i1<len1; i1++){
if(typeof data8[i1] !== "string"){
const err23 = {instancePath:instancePath+"/results/" + i0+"/limitations/" + i1,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/limitations/items/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err23];
}
else {
vErrors.push(err23);
}
errors++;
}
}
}
else {
const err24 = {instancePath:instancePath+"/results/" + i0+"/limitations",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/limitations/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err24];
}
else {
vErrors.push(err24);
}
errors++;
}
}
if(data2.supersedes_result_id !== undefined){
let data10 = data2.supersedes_result_id;
const _errs24 = errors;
let valid7 = false;
const _errs25 = errors;
if(typeof data10 === "string"){
if(!(formats0.test(data10))){
const err25 = {instancePath:instancePath+"/results/" + i0+"/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/0/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err25];
}
else {
vErrors.push(err25);
}
errors++;
}
}
else {
const err26 = {instancePath:instancePath+"/results/" + i0+"/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/0/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err26];
}
else {
vErrors.push(err26);
}
errors++;
}
var _valid0 = _errs25 === errors;
valid7 = valid7 || _valid0;
const _errs27 = errors;
if(data10 !== null){
const err27 = {instancePath:instancePath+"/results/" + i0+"/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf/1/type",keyword:"type",params:{type: "null"},message:"must be null"};
if(vErrors === null){
vErrors = [err27];
}
else {
vErrors.push(err27);
}
errors++;
}
var _valid0 = _errs27 === errors;
valid7 = valid7 || _valid0;
if(!valid7){
const err28 = {instancePath:instancePath+"/results/" + i0+"/supersedes_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/supersedes_result_id/anyOf",keyword:"anyOf",params:{},message:"must match a schema in anyOf"};
if(vErrors === null){
vErrors = [err28];
}
else {
vErrors.push(err28);
}
errors++;
}
else {
errors = _errs24;
if(vErrors !== null){
if(_errs24){
vErrors.length = _errs24;
}
else {
vErrors = null;
}
}
}
}
if(data2.created_at !== undefined){
let data11 = data2.created_at;
if(typeof data11 === "string"){
if(!(formats2.validate(data11))){
const err29 = {instancePath:instancePath+"/results/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/created_at/format",keyword:"format",params:{format: "date-time"},message:"must match format \""+"date-time"+"\""};
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
const err30 = {instancePath:instancePath+"/results/" + i0+"/created_at",schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/properties/created_at/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err30];
}
else {
vErrors.push(err30);
}
errors++;
}
}
}
else {
const err31 = {instancePath:instancePath+"/results/" + i0,schemaPath:"urn:wuji:contracts:0.5#/$defs/VerificationResult/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
const err32 = {instancePath:instancePath+"/results",schemaPath:"#/properties/results/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err32];
}
else {
vErrors.push(err32);
}
errors++;
}
}
if(data.evidence !== undefined){
let data12 = data.evidence;
if(Array.isArray(data12)){
if(data12.length > 200){
const err33 = {instancePath:instancePath+"/evidence",schemaPath:"#/properties/evidence/maxItems",keyword:"maxItems",params:{limit: 200},message:"must NOT have more than 200 items"};
if(vErrors === null){
vErrors = [err33];
}
else {
vErrors.push(err33);
}
errors++;
}
const len2 = data12.length;
for(let i2=0; i2<len2; i2++){
let data13 = data12[i2];
if(data13 && typeof data13 == "object" && !Array.isArray(data13)){
if(data13.id === undefined){
const err34 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "id"},message:"must have required property '"+"id"+"'"};
if(vErrors === null){
vErrors = [err34];
}
else {
vErrors.push(err34);
}
errors++;
}
if(data13.verification_result_id === undefined){
const err35 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "verification_result_id"},message:"must have required property '"+"verification_result_id"+"'"};
if(vErrors === null){
vErrors = [err35];
}
else {
vErrors.push(err35);
}
errors++;
}
if(data13.observation_id === undefined){
const err36 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "observation_id"},message:"must have required property '"+"observation_id"+"'"};
if(vErrors === null){
vErrors = [err36];
}
else {
vErrors.push(err36);
}
errors++;
}
if(data13.artifact_id === undefined){
const err37 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "artifact_id"},message:"must have required property '"+"artifact_id"+"'"};
if(vErrors === null){
vErrors = [err37];
}
else {
vErrors.push(err37);
}
errors++;
}
if(data13.relation === undefined){
const err38 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "relation"},message:"must have required property '"+"relation"+"'"};
if(vErrors === null){
vErrors = [err38];
}
else {
vErrors.push(err38);
}
errors++;
}
if(data13.selector === undefined){
const err39 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/required",keyword:"required",params:{missingProperty: "selector"},message:"must have required property '"+"selector"+"'"};
if(vErrors === null){
vErrors = [err39];
}
else {
vErrors.push(err39);
}
errors++;
}
for(const key2 in data13){
if(!((((((key2 === "id") || (key2 === "verification_result_id")) || (key2 === "observation_id")) || (key2 === "artifact_id")) || (key2 === "relation")) || (key2 === "selector"))){
const err40 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/additionalProperties",keyword:"additionalProperties",params:{additionalProperty: key2},message:"must NOT have additional properties"};
if(vErrors === null){
vErrors = [err40];
}
else {
vErrors.push(err40);
}
errors++;
}
}
if(data13.id !== undefined){
let data14 = data13.id;
if(typeof data14 === "string"){
if(!(formats0.test(data14))){
const err41 = {instancePath:instancePath+"/evidence/" + i2+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err41];
}
else {
vErrors.push(err41);
}
errors++;
}
}
else {
const err42 = {instancePath:instancePath+"/evidence/" + i2+"/id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err42];
}
else {
vErrors.push(err42);
}
errors++;
}
}
if(data13.verification_result_id !== undefined){
let data15 = data13.verification_result_id;
if(typeof data15 === "string"){
if(!(formats0.test(data15))){
const err43 = {instancePath:instancePath+"/evidence/" + i2+"/verification_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/verification_result_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err43];
}
else {
vErrors.push(err43);
}
errors++;
}
}
else {
const err44 = {instancePath:instancePath+"/evidence/" + i2+"/verification_result_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/verification_result_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err44];
}
else {
vErrors.push(err44);
}
errors++;
}
}
if(data13.observation_id !== undefined){
let data16 = data13.observation_id;
if(typeof data16 === "string"){
if(!(formats0.test(data16))){
const err45 = {instancePath:instancePath+"/evidence/" + i2+"/observation_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/observation_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err45];
}
else {
vErrors.push(err45);
}
errors++;
}
}
else {
const err46 = {instancePath:instancePath+"/evidence/" + i2+"/observation_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/observation_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err46];
}
else {
vErrors.push(err46);
}
errors++;
}
}
if(data13.artifact_id !== undefined){
let data17 = data13.artifact_id;
if(typeof data17 === "string"){
if(!(formats0.test(data17))){
const err47 = {instancePath:instancePath+"/evidence/" + i2+"/artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/artifact_id/format",keyword:"format",params:{format: "uuid"},message:"must match format \""+"uuid"+"\""};
if(vErrors === null){
vErrors = [err47];
}
else {
vErrors.push(err47);
}
errors++;
}
}
else {
const err48 = {instancePath:instancePath+"/evidence/" + i2+"/artifact_id",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/artifact_id/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err48];
}
else {
vErrors.push(err48);
}
errors++;
}
}
if(data13.relation !== undefined){
let data18 = data13.relation;
if(typeof data18 !== "string"){
const err49 = {instancePath:instancePath+"/evidence/" + i2+"/relation",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/relation/type",keyword:"type",params:{type: "string"},message:"must be string"};
if(vErrors === null){
vErrors = [err49];
}
else {
vErrors.push(err49);
}
errors++;
}
if(!(((data18 === "supports") || (data18 === "refutes")) || (data18 === "limits"))){
const err50 = {instancePath:instancePath+"/evidence/" + i2+"/relation",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/relation/enum",keyword:"enum",params:{allowedValues: schema128.properties.relation.enum},message:"must be equal to one of the allowed values"};
if(vErrors === null){
vErrors = [err50];
}
else {
vErrors.push(err50);
}
errors++;
}
}
if(data13.selector !== undefined){
let data19 = data13.selector;
if(data19 && typeof data19 == "object" && !Array.isArray(data19)){
}
else {
const err51 = {instancePath:instancePath+"/evidence/" + i2+"/selector",schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/properties/selector/type",keyword:"type",params:{type: "object"},message:"must be object"};
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
else {
const err52 = {instancePath:instancePath+"/evidence/" + i2,schemaPath:"urn:wuji:contracts:0.5#/$defs/EvidenceLink/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err52];
}
else {
vErrors.push(err52);
}
errors++;
}
}
}
else {
const err53 = {instancePath:instancePath+"/evidence",schemaPath:"#/properties/evidence/type",keyword:"type",params:{type: "array"},message:"must be array"};
if(vErrors === null){
vErrors = [err53];
}
else {
vErrors.push(err53);
}
errors++;
}
}
}
else {
const err54 = {instancePath,schemaPath:"#/type",keyword:"type",params:{type: "object"},message:"must be object"};
if(vErrors === null){
vErrors = [err54];
}
else {
vErrors.push(err54);
}
errors++;
}
validate108.errors = vErrors;
return errors === 0;
}
validate108.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};

export const validateError = validate110;
const schema129 = {"type":"object","additionalProperties":false,"required":["code","message","trace_id"],"properties":{"code":{"type":"string","enum":["UNAUTHENTICATED","FORBIDDEN","NOT_FOUND","VALIDATION_FAILED","SCOPE_DENIED","PREVIEW_EXPIRED","VERSION_CONFLICT","IDEMPOTENCY_CONFLICT","INVALID_TRANSITION","RATE_LIMITED","SERVICE_UNAVAILABLE","CURSOR_EXPIRED","INTERNAL_ERROR"]},"message":{"type":"string","minLength":1,"maxLength":500},"trace_id":{"type":"string","format":"uuid"},"field_errors":{"type":"array","maxItems":30,"items":{"type":"object","additionalProperties":false,"required":["field","message"],"properties":{"field":{"type":"string","minLength":1,"maxLength":128},"message":{"type":"string","minLength":1,"maxLength":300}}}}}};

function validate110(data, {instancePath="", parentData, parentDataProperty, rootData=data, dynamicAnchors={}}={}){
let vErrors = null;
let errors = 0;
const evaluated0 = validate110.evaluated;
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
const err5 = {instancePath:instancePath+"/code",schemaPath:"#/properties/code/enum",keyword:"enum",params:{allowedValues: schema129.properties.code.enum},message:"must be equal to one of the allowed values"};
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
validate110.errors = vErrors;
return errors === 0;
}
validate110.evaluated = {"props":true,"dynamicProps":false,"dynamicItems":false};
